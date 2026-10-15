"""Gardien anti-fraude : repère les comportements frauduleux et réagit seul, sans jamais sanctionner.

Décision de l'utilisateur (15 oct. 2026) : le Gardien peut seulement prendre des mesures réversibles
(mettre un compte en pause, bloquer les espèces, retenir les versements d'un commerce) et prévenir
l'admin. La sanction définitive (désactivation) est toujours décidée par l'admin.

Les règles sont fixes et chiffrées (jamais le seul avis du modèle de langage, qui peut être trompé) :
- elles comptent des faits enregistrés (reçus refusés, ID déjà utilisés, codes PIN faux, annulations,
  livraisons refusées, problèmes signalés) sur une période ;
- après un déblocage par l'admin, seuls les faits postérieurs comptent (pas de re-blocage en boucle) ;
- chaque mesure prévient la personne concernée (pourquoi, que faire), les personnes qu'elle protège et l'admin.
"""
import logging
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.db.models import F, Q
from django.utils import timezone

logger = logging.getLogger(__name__)

SUPPORT_STEP = (
	"Demandez à l'assistant Gaboshop ce qui se passe, ou contactez le support : "
	"un administrateur vérifie votre dossier et lève la mesure si tout est en ordre."
)

# Règles : rôle visé, période, seuil, mesure prise, texte pour la personne, texte pour l'admin.
RULES = {
	'client_faux_paiements': {
		'role': 'client', 'days': 30, 'threshold': 3, 'kind': 'pause',
		'user_reason': "Plusieurs paiements Mobile Money déclarés sur votre compte n'ont pas été reçus par les commerces "
		               "ou utilisaient un ID de transaction déjà servi.",
		'admin': 'paiements déclarés refusés ou ID de transaction réutilisés',
	},
	'client_refus_livraison': {
		'role': 'client', 'days': 30, 'threshold': 2, 'kind': 'cash_block',
		'user_reason': "Plusieurs commandes payables en espèces n'ont pas pu être remises (livraison en échec).",
		'admin': 'livraisons payables en espèces en échec',
	},
	'client_reclamations': {
		'role': 'client', 'days': 30, 'threshold': 3, 'kind': 'pause',
		'user_reason': "Un nombre inhabituel de problèmes a été signalé sur vos commandes livrées.",
		'admin': 'problèmes signalés après livraison',
	},
	'commerce_annulations': {
		'role': 'store_manager', 'days': 7, 'threshold': 3, 'kind': 'payout_freeze',
		'user_reason': "Votre commerce a annulé plusieurs commandes en peu de temps.",
		'admin': 'commandes annulées par le commerce',
	},
	'commerce_litiges': {
		'role': 'store_manager', 'days': 14, 'threshold': 3, 'kind': 'payout_freeze',
		'user_reason': "Plusieurs clients différents ont signalé un problème sur des commandes de votre commerce.",
		'admin': 'commandes du commerce avec un problème signalé',
	},
	'codes_pin_faux': {
		'role': ('delivery_agent', 'store_manager'), 'days': 1, 'threshold': 3, 'kind': 'pause',
		'user_reason': "Des codes PIN de livraison faux ont été saisis sur plusieurs commandes depuis votre compte.",
		'admin': 'livraisons avec des codes PIN faux (sur des commandes différentes)',
	},
	'livreur_litiges': {
		'role': 'delivery_agent', 'days': 14, 'threshold': 2, 'kind': 'pause',
		'user_reason': "Plusieurs clients ont signalé un problème sur des commandes que vous avez livrées.",
		'admin': 'livraisons du livreur suivies d’un problème signalé',
	},
	'livreur_sa_propre_commande': {
		'role': 'delivery_agent', 'days': 30, 'threshold': 1, 'kind': 'alert',
		'user_reason': "",
		'admin': 'courses livrées par le livreur sur ses propres commandes de client',
	},
}

# Un commerce qui saisit des PIN faux voit ses versements retenus (il ne prend pas de course).
KIND_FOR_ROLE = {('codes_pin_faux', 'store_manager'): 'payout_freeze'}

KIND_TITLES = {
	'pause': 'Compte en pause le temps d’une vérification',
	'cash_block': 'Paiement en espèces suspendu',
	'payout_freeze': 'Versements retenus le temps d’une vérification',
	'alert': '',
}

KIND_EFFECTS = {
	'pause': "Vous pouvez toujours vous connecter et consulter vos commandes, mais pas en passer de nouvelles, "
	         "déclarer un paiement ni prendre de course.",
	'cash_block': "Vos prochaines commandes se paient par Mobile Money (paiement en ligne ou code marchand).",
	'payout_freeze': "Vos ventes restent enregistrées et votre argent est conservé, mais il ne vous sera versé "
	                 "qu'après la vérification.",
	'alert': '',
}


def _role(user):
	if user is None or not getattr(user, 'is_authenticated', False):
		return None
	if user.is_staff or user.is_superuser or user.user_type == 'admin':
		return 'admin'
	return user.user_type


def _rule_applies(rule, role):
	roles = RULES[rule]['role']
	return role in (roles if isinstance(roles, tuple) else (roles,))


def _since(user, rule):
	"""Début de la période, ou dernier déblocage par l'admin s'il est plus récent."""
	start = timezone.now() - timedelta(days=RULES[rule]['days'])
	from core.models import RiskHold
	lifted = (
		RiskHold.objects.filter(user=user, rule=rule, status='lifted').exclude(decided_at=None)
		.order_by('-decided_at').values_list('decided_at', flat=True).first()
	)
	return max(start, lifted) if lifted else start


def _managed_store(user):
	from stores.models import Store
	return Store.objects.filter(manager=user).order_by('id').first()


# ---------- Mesure des règles ----------

def _measure(rule, user, since):
	"""Renvoie (nombre, preuves) pour une règle."""
	from core.models import FraudSignal
	from orders.models import Order
	if rule == 'client_faux_paiements':
		from payments.direct_models import PaymentReceipt
		refused = PaymentReceipt.objects.filter(actor=user, status='rejected', rejected_at__gte=since)
		rejected = list(refused.values_list('reference', flat=True)[:10])
		reviewers = refused.values('rejected_by').distinct().count()
		reused = list(
			FraudSignal.objects.filter(user=user, kind='receipt_reused', created_at__gte=since)
			.values_list('detail', flat=True)[:10]
		)
		# Un seul commerce qui refuse tout ne suffit pas à mettre un client en pause (il pourrait mentir) :
		# ses refus comptent au plus pour 2. Les ID déjà utilisés, eux, sont un fait vérifié.
		counted = len(rejected) if reviewers >= 2 else min(len(rejected), RULES[rule]['threshold'] - 1)
		return counted + len(reused), {'recus_refuses': rejected, 'refuse_par': reviewers, 'id_deja_utilises': reused}
	if rule == 'client_refus_livraison':
		from delivery.models import Delivery
		failed = list(
			Delivery.objects.filter(order__client=user, status='failed', updated_at__gte=since)
			.filter(Q(order__payment_arrangement__method='cash') | Q(order__payment_arrangement__flow='courier_cash'))
			.values_list('order__order_number', flat=True)[:10]
		)
		return len(failed), {'commandes': failed}
	if rule == 'client_reclamations':
		orders = list(
			Order.objects.filter(client=user, client_problem_reported_at__gte=since)
			.values_list('order_number', flat=True)[:10]
		)
		return len(orders), {'commandes': orders}
	if rule == 'commerce_annulations':
		orders = list(
			FraudSignal.objects.filter(user=user, kind='store_cancel', created_at__gte=since)
			.values_list('detail', flat=True)[:10]
		)
		return len(orders), {'commandes': orders}
	if rule == 'commerce_litiges':
		store = _managed_store(user)
		if store is None:
			return 0, {}
		qs = Order.objects.filter(store=store, client_problem_reported_at__gte=since)
		clients = qs.values('client').distinct().count()
		orders = list(qs.values_list('order_number', flat=True)[:10])
		# Un seul client qui se plaint souvent relève de la règle client, pas du commerce.
		return (len(orders) if clients >= 2 else 0), {'commandes': orders, 'clients_differents': clients}
	if rule == 'codes_pin_faux':
		signals = FraudSignal.objects.filter(user=user, kind='pin_failure', created_at__gte=since)
		deliveries = signals.values('delivery_id').distinct().count()
		total = signals.count()
		# 3 commandes différentes, ou 8 essais faux en tout : ce n'est plus une faute de frappe.
		count = deliveries if total < 8 else max(deliveries, RULES[rule]['threshold'])
		return count, {'livraisons_differentes': deliveries, 'essais_faux': total}
	if rule == 'livreur_litiges':
		qs = Order.objects.filter(delivery__delivery_agent=user, client_problem_reported_at__gte=since)
		clients = qs.values('client').distinct().count()
		orders = list(qs.values_list('order_number', flat=True)[:10])
		# Un seul client mécontent ne suffit pas : il faut des clients différents.
		return (len(orders) if clients >= 2 else 0), {'commandes': orders, 'clients_differents': clients}
	if rule == 'livreur_sa_propre_commande':
		from delivery.models import Delivery
		orders = list(
			Delivery.objects.filter(delivery_agent=user, order__client=user, updated_at__gte=since)
			.values_list('order__order_number', flat=True)[:10]
		)
		return len(orders), {'commandes': orders}
	return 0, {}


# ---------- Enregistrer des indices ----------

def record_signal(kind, user, order=None, delivery=None, store=None, detail=''):
	"""Enregistre un indice puis réévalue le compte. Ne casse jamais l'action en cours."""
	if _role(user) in (None, 'admin'):
		return
	try:
		from core.models import FraudSignal
		FraudSignal.objects.create(
			kind=kind, user=user, detail=str(detail or '')[:255],
			order_id=getattr(order, 'id', None), delivery_id=getattr(delivery, 'id', None),
			store_id=getattr(store, 'id', None),
		)
		evaluate(user)
	except Exception:
		logger.exception('Gardien : indice %s non enregistré', kind)


def check(user):
	"""Réévalue un compte après un fait déjà enregistré ailleurs (reçu refusé, problème signalé…)."""
	try:
		return evaluate(user)
	except Exception:
		logger.exception('Gardien : évaluation impossible pour %s', getattr(user, 'id', None))
		return []


# ---------- Évaluer et agir ----------

def evaluate(user):
	"""Applique les règles du rôle de ce compte. Renvoie les nouvelles mesures prises."""
	role = _role(user)
	if role in (None, 'admin', 'visitor') or not user.is_active:
		return []
	from core.models import RiskHold
	active = set(RiskHold.objects.filter(user=user, status='active').values_list('rule', flat=True))
	created = []
	for rule, spec in RULES.items():
		if rule in active or not _rule_applies(rule, role):
			continue
		count, evidence = _measure(rule, user, _since(user, rule))
		if count < spec['threshold']:
			continue
		hold = _open_hold(user, rule, role, count, evidence)
		if hold is not None:
			created.append(hold)
	return created


def _open_hold(user, rule, role, count, evidence):
	from core.models import AuditLog, RiskHold
	spec = RULES[rule]
	kind = KIND_FOR_ROLE.get((rule, role), spec['kind'])
	store = _managed_store(user) if kind == 'payout_freeze' or role == 'store_manager' else None
	if kind == 'payout_freeze' and store is None:
		kind = 'alert'
	try:
		with transaction.atomic():
			previous = {}
			if kind == 'pause' and role == 'delivery_agent':
				previous['is_available'] = user.is_available
				if user.is_available:
					user.is_available = False
					user.save(update_fields=['is_available'])
			if kind == 'payout_freeze':
				previous['payouts_frozen'] = store.payouts_frozen
				if not store.payouts_frozen:
					store.payouts_frozen = True
					store.save(update_fields=['payouts_frozen', 'updated_at'])
			hold = RiskHold.objects.create(
				user=user, store=store, kind=kind, rule=rule,
				reason=spec['user_reason'] or spec['admin'],
				evidence={'nombre': count, 'seuil': spec['threshold'], 'jours': spec['days'], **evidence},
				previous=previous,
			)
	except IntegrityError:
		return None  # une autre requête vient de prendre la même mesure
	try:
		AuditLog.log_action(
			'fraud_detected', user, 'user', user.id, new_value={'mesure': kind, 'regle': rule},
			reason=f"Gardien anti-fraude : {count} {spec['admin']} en {spec['days']} j", is_suspicious=True,
		)
	except Exception:
		logger.exception('Gardien : journal non écrit')
	_announce(hold, role, count)
	return hold


def _notify(user, title, body, level, reason='', next_step='', metadata=None, notif_type='warning'):
	try:
		from notifications.service import NotificationService
		NotificationService.notify_user(user, {
			'title': title, 'body': body, 'level': level, 'reason': reason, 'next_step': next_step,
		}, notif_type=notif_type, metadata={'source': 'gardien', **(metadata or {})})
	except Exception:
		logger.exception('Gardien : notification non envoyée')


def _admins():
	from users.models import User
	return User.objects.filter(is_active=True).filter(Q(user_type='admin') | Q(is_staff=True) | Q(is_superuser=True))


def _announce(hold, role, count):
	spec = RULES[hold.rule]
	who = f"{hold.user.get_full_name() or hold.user.phone} ({hold.user.get_user_type_display()})"
	if hold.store_id:
		who += f" — {hold.store.name}"
	action = {
		'pause': 'compte mis en pause', 'cash_block': 'espèces bloquées',
		'payout_freeze': 'versements retenus', 'alert': 'aucune mesure, à vérifier',
	}[hold.kind]
	for admin in _admins():
		_notify(
			admin, f"Gardien anti-fraude : {who}",
			f"{count} {spec['admin']} en {spec['days']} jours. Mesure prise seule : {action}.",
			'warning', reason='Mesure réversible prise par le Gardien en attendant votre décision.',
			next_step='Ouvrez le tableau de bord admin, rubrique « Gardien anti-fraude » : Débloquer ou Sanctionner.',
			metadata={'action': 'gardien', 'hold_id': hold.id},
		)
	if hold.kind == 'alert':
		return
	_notify(
		hold.user, KIND_TITLES[hold.kind], f"{hold.reason} {KIND_EFFECTS[hold.kind]}", 'warning',
		reason=hold.reason, next_step=SUPPORT_STEP, metadata={'hold_id': hold.id},
	)
	_protect_others(hold, role)


def _protect_others(hold, role):
	"""Prévient les personnes que la mesure protège."""
	from orders.models import Order
	if hold.kind == 'pause' and role == 'client':
		stores = (
			Order.objects.filter(client=hold.user, status__in=('pending', 'confirmed', 'preparing'))
			.select_related('store__manager')
		)
		seen = set()
		for order in stores[:20]:
			manager = order.store.manager if order.store_id else None
			if manager is None or manager.id in seen:
				continue
			seen.add(manager.id)
			_notify(
				manager, f"Prudence sur la commande {order.order_number}",
				"Le compte de ce client est en vérification chez Gaboshop. Ne préparez la commande qu'une fois "
				"le paiement réellement reçu (vérifiez votre SMS Mobile Money).",
				'warning', reason="Des paiements déclarés par ce client n'ont pas été reçus ou des problèmes ont été signalés.",
				next_step="En cas de doute, refusez le paiement déclaré : Gaboshop tranchera.",
				metadata={'order_id': order.id}, notif_type='order',
			)
	if hold.kind == 'pause' and role == 'delivery_agent':
		active = Order.objects.filter(
			delivery__delivery_agent=hold.user,
			delivery__status__in=('assigned', 'accepted', 'accepted_by_driver', 'picked_up', 'in_delivery', 'in_transit'),
		)
		for order in active[:20]:
			_notify(
				order.client, f"Commande {order.order_number} : gardez votre code PIN",
				"Ne donnez votre code PIN au livreur qu'une fois le colis en main et vérifié.",
				'warning', reason='Gaboshop vérifie le compte du livreur chargé de votre commande.',
				next_step="S'il y a un souci à la remise, signalez un problème dans votre commande.",
				metadata={'order_id': order.id}, notif_type='delivery',
			)


# ---------- Décisions de l'admin ----------

@transaction.atomic
def lift(hold, admin, note=''):
	"""Débloquer : la mesure est levée et l'état d'avant est rétabli."""
	from core.models import RiskHold
	hold = RiskHold.objects.select_for_update().get(pk=hold.pk)
	if hold.status != 'active':
		return hold
	hold.status, hold.decided_at, hold.decided_by, hold.admin_note = 'lifted', timezone.now(), admin, note[:1000]
	hold.save(update_fields=['status', 'decided_at', 'decided_by', 'admin_note'])
	others = RiskHold.objects.filter(user=hold.user, status='active')
	if hold.kind == 'pause' and hold.previous.get('is_available') and not others.filter(kind='pause').exists():
		hold.user.is_available = True
		hold.user.save(update_fields=['is_available'])
	if hold.kind == 'payout_freeze' and hold.store_id and hold.previous.get('payouts_frozen') is False \
			and not RiskHold.objects.filter(store=hold.store, status='active', kind='payout_freeze').exists():
		store = hold.store
		store.payouts_frozen = False
		store.save(update_fields=['payouts_frozen', 'updated_at'])
		transaction.on_commit(lambda: _release_frozen(store))
	_audit(admin, hold, 'levée')
	if hold.kind != 'alert':
		_notify(
			hold.user, 'Vérification terminée : mesure levée',
			"Gaboshop a vérifié votre compte. Tout est rétabli, vous pouvez utiliser l'application normalement.",
			'success', metadata={'hold_id': hold.id}, notif_type='info',
		)
	return hold


@transaction.atomic
def sanction(hold, admin, note=''):
	"""Sanctionner : décision de l'admin seulement. Le compte (et le commerce) est désactivé."""
	from core.models import RiskHold
	hold = RiskHold.objects.select_for_update().get(pk=hold.pk)
	if hold.status != 'active':
		return hold
	user = hold.user
	now = timezone.now()
	RiskHold.objects.filter(user=user, status='active').update(
		status='sanctioned', decided_at=now, decided_by=admin, admin_note=note[:1000],
	)
	user.is_active = False
	user.save(update_fields=['is_active'])
	from stores.models import Store
	Store.objects.filter(manager=user, is_active=True).update(is_active=False)
	try:
		from users.password_reset import revoke_refresh_tokens
		revoke_refresh_tokens(user)
	except Exception:
		logger.exception('Gardien : sessions non coupées')
	hold.refresh_from_db()
	_audit(admin, hold, 'sanction')
	return hold


def _release_frozen(store):
	from payments.models import StorePayout
	from payments.store_payout_service import FROZEN_NOTE, release_store_payment
	for payout in StorePayout.objects.filter(store=store, status='pending', note=FROZEN_NOTE):
		try:
			release_store_payment(payout.order_id)
		except Exception:
			logger.exception('Gardien : versement %s non relancé', payout.id)


def _audit(admin, hold, decision):
	try:
		from core.models import AuditLog
		AuditLog.log_action(
			'fraud_detected', admin, 'user', hold.user_id, new_value={'decision': decision, 'regle': hold.rule},
			reason=f'Gardien anti-fraude : {decision} par l’admin. {hold.admin_note}'.strip(),
		)
	except Exception:
		logger.exception('Gardien : journal non écrit')


# ---------- Ce que le reste de l'application vérifie ----------

def active_holds(user, kinds=None):
	from core.models import RiskHold
	if user is None or not getattr(user, 'is_authenticated', False):
		return RiskHold.objects.none()
	qs = RiskHold.objects.filter(user=user, status='active')
	return qs.filter(kind__in=kinds) if kinds else qs


def pause_refusal(user):
	"""Message d'erreur si le compte est en pause, sinon None."""
	hold = active_holds(user, ('pause',)).first()
	if hold is None:
		return None
	return {
		'code': 'compte_en_pause',
		'message': 'Votre compte est en pause le temps d’une vérification par Gaboshop.',
		'reason': hold.reason,
		'next_step': SUPPORT_STEP,
	}


def cash_blocked(user):
	return active_holds(user, ('cash_block',)).exists()


def paused_user_ids():
	from core.models import RiskHold
	return RiskHold.objects.filter(status='active', kind='pause').values_list('user_id', flat=True)


def holds_payload(qs):
	return [{
		'id': h.id, 'user_id': h.user_id, 'user': h.user.get_full_name() or h.user.phone, 'phone': h.user.phone,
		'role': h.user.get_user_type_display(), 'store': h.store.name if h.store_id else None,
		'kind': h.kind, 'kind_label': h.get_kind_display(), 'rule': h.rule,
		'why': f"{h.evidence.get('nombre')} {RULES.get(h.rule, {}).get('admin', h.rule)} en {h.evidence.get('jours')} jours",
		'evidence': h.evidence, 'status': h.status, 'created_at': h.created_at,
	} for h in qs.select_related('user', 'store')]


# ---------- Tâche automatique ----------

def scan_recent():
	"""Passe régulière : réévalue les comptes qui ont eu de l'activité suspecte ces 2 derniers jours."""
	from core.models import FraudSignal
	from delivery.models import Delivery
	from orders.models import Order
	from payments.direct_models import PaymentReceipt
	from users.models import User
	since = timezone.now() - timedelta(days=2)
	ids = set(FraudSignal.objects.filter(created_at__gte=since).values_list('user_id', flat=True))
	ids |= set(PaymentReceipt.objects.filter(status='rejected', rejected_at__gte=since).values_list('actor_id', flat=True))
	problems = Order.objects.filter(client_problem_reported_at__gte=since)
	ids |= set(problems.values_list('client_id', flat=True))
	ids |= set(problems.values_list('store__manager_id', flat=True))
	ids |= set(problems.exclude(delivery__delivery_agent=None).values_list('delivery__delivery_agent_id', flat=True))
	ids |= set(Delivery.objects.filter(status='failed', updated_at__gte=since).values_list('order__client_id', flat=True))
	ids |= set(Delivery.objects.filter(updated_at__gte=since, delivery_agent__isnull=False)
	           .filter(order__client_id=F('delivery_agent_id')).values_list('delivery_agent_id', flat=True))
	ids.discard(None)
	created = 0
	for user in User.objects.filter(id__in=ids, is_active=True):
		created += len(check(user))
	return f'{len(ids)} compte(s) réexaminé(s), {created} nouvelle(s) mesure(s)'
