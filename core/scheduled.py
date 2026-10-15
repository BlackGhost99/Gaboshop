"""Tâches automatiques de Gaboshop, sans worker Celery.

Render gratuit n'a pas de worker : un minuteur (GitHub Actions) appelle POST /api/v1/internal/tick/
toutes les quelques minutes, et chaque passage lance les tâches dont l'heure est venue.
Chaque tâche est « réservée » en base avant de tourner : deux appels simultanés ne la lancent pas deux fois.
"""
import logging
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)

# Paiements en ligne : on interroge SingPay après 2 min, et plus du tout au-delà de 24 h.
PAYMENT_CHECK_AFTER = timedelta(minutes=2)
PAYMENT_CHECK_UNTIL = timedelta(hours=24)
PAYMENT_CHECKS_PER_TICK = 20


def _claim(name, every):
	"""Réserve la tâche si son dernier passage date d'au moins `every`. Renvoie True si on doit la lancer."""
	from core.models import ScheduledTaskRun
	now = timezone.now()
	ScheduledTaskRun.objects.get_or_create(name=name)
	return bool(
		ScheduledTaskRun.objects.filter(name=name)
		.filter(Q(last_run_at__isnull=True) | Q(last_run_at__lte=now - every))
		.update(last_run_at=now)
	)


def _record(name, ok, message):
	from core.models import ScheduledTaskRun
	ScheduledTaskRun.objects.filter(name=name).update(last_ok=ok, last_message=str(message)[:2000])


def advance_deliveries():
	"""Relance l'attribution des livreurs : commandes prêtes sans livreur, délais de réponse dépassés, diffusion à tous."""
	from delivery.assignment_flow import (
		ACCEPTED_STATUSES, _should_broadcast, assignment_timeout_minutes, broadcast_if_unaccepted,
		handle_assignment_timeout, start_delivery_assignment,
	)
	from delivery.models import Delivery
	from orders.models import Order

	now = timezone.now()
	started = timed_out = broadcast = 0
	waiting = Order.objects.filter(status='ready').filter(
		Q(delivery__isnull=True) | Q(delivery__delivery_agent__isnull=True, delivery__is_open_to_all=False)
	).select_related('store')
	for order in waiting:
		try:
			if start_delivery_assignment(order) is not None:
				started += 1
		except Exception:
			logger.exception('Attribution impossible pour la commande %s', order.order_number)

	pending = Delivery.objects.filter(
		auto_assignment_enabled=True, accepted_at__isnull=True, is_open_to_all=False,
	).exclude(status__in=ACCEPTED_STATUSES)
	timeout = timedelta(minutes=assignment_timeout_minutes())
	for delivery in pending.filter(status='assigned', assigned_at__lte=now - timeout):
		try:
			handle_assignment_timeout(delivery.id, delivery.assignment_round)
			timed_out += 1
		except Exception:
			logger.exception('Délai de réponse du livreur non traité (livraison %s)', delivery.id)
	for delivery in pending.filter(assignment_started_at__isnull=False):
		if _should_broadcast(delivery.assignment_started_at, now):
			try:
				broadcast_if_unaccepted(delivery.id)
				broadcast += 1
			except Exception:
				logger.exception('Diffusion de la course impossible (livraison %s)', delivery.id)
	return f'{started} attribution(s) relancée(s), {timed_out} délai(s) dépassé(s), {broadcast} course(s) ouvertes à tous'


def check_online_payments():
	"""Demande à SingPay le résultat des paiements en ligne restés en attente (le client a pu valider sans retour)."""
	from payments.models import Payment
	from payments.online_verification import verify_order_payment

	now = timezone.now()
	payments = Payment.objects.filter(
		status__in=('pending', 'processing'), payment_method__in=('airtel_money', 'moov_money'),
		created_at__lte=now - PAYMENT_CHECK_AFTER, created_at__gte=now - PAYMENT_CHECK_UNTIL,
	).select_related('order').order_by('updated_at')[:PAYMENT_CHECKS_PER_TICK]
	results = {}
	for payment in payments:
		try:
			outcome = verify_order_payment(payment, 'vérification automatique')
		except Exception:
			logger.exception('Vérification SingPay impossible pour le paiement %s', payment.pk)
			outcome = 'erreur'
		results[outcome] = results.get(outcome, 0) + 1
	# Abonnements de commerce et forfaits clients (PaymentIntent) : sans notification de SingPay,
	# ils resteraient « en attente » alors que l'argent est parti.
	from payments.models import PaymentIntent
	from payments.online_verification import verify_intent
	from payments.views import process_intent_outcome
	intents = PaymentIntent.objects.filter(
		provider='singpay', status='PENDING',
		created_at__lte=now - PAYMENT_CHECK_AFTER, created_at__gte=now - PAYMENT_CHECK_UNTIL,
	).order_by('created_at')[:PAYMENT_CHECKS_PER_TICK]
	for intent in intents:
		try:
			outcome, provider_tx_id, raw = verify_intent(intent)
			if outcome != 'unknown' and provider_tx_id:
				process_intent_outcome(intent, provider_tx_id, outcome, raw)
			outcome = f'abonnement {outcome}'
		except Exception:
			logger.exception('Vérification SingPay impossible pour l’abonnement %s', intent.reference)
			outcome = 'abonnement erreur'
		results[outcome] = results.get(outcome, 0) + 1
	return ', '.join(f'{n} {k}' for k, n in results.items()) or 'aucun paiement en attente'


def cancel_abandoned_orders():
	"""Annule les commandes jamais payées ni prises en charge après le délai réglé dans l'admin, et remet le stock."""
	from api.models import SystemSettings
	from notifications.service import NotificationService
	from orders.models import Order
	from orders.services import OrderService
	from payments.online_verification import verify_order_payment

	hours = int(SystemSettings.current('cart_validity_hours', 24) or 24)
	limit = timezone.now() - timedelta(hours=hours)
	orders = Order.objects.filter(status__in=('created', 'pending_payment'), created_at__lt=limit).exclude(
		# Un paiement Mobile Money déclaré au commerce attend sa vérification : on ne touche à rien.
		payment_arrangement__obligations__receipts__status__in=('pending', 'confirmed'),
	).distinct()
	cancelled = 0
	for order in orders:
		payment = getattr(order, 'payment', None)
		try:
			if payment is not None and payment.status != 'success' and payment.payment_method in ('airtel_money', 'moov_money'):
				verify_order_payment(payment, 'avant annulation automatique')
				payment.refresh_from_db()
			if payment is not None and payment.status == 'success':
				continue
			order.refresh_from_db()
			if order.status not in ('created', 'pending_payment'):
				continue
			old_status = order.status
			OrderService.cancel_order(order, reason=f'non payée ni prise en charge après {hours} h')
			cancelled += 1
			try:
				NotificationService.notify_order_status_update(order, old_status, 'cancelled')
			except Exception:
				logger.exception('Notification d’annulation impossible (%s)', order.order_number)
		except Exception:
			logger.exception('Annulation automatique impossible pour la commande %s', order.order_number)
	return f'{cancelled} commande(s) abandonnée(s) annulée(s), stock remis en vente'


def expire_subscriptions():
	"""Passe en « expiré » les abonnements de commerce dont la date de fin est passée."""
	from payments.models import StoreSubscription
	today = timezone.now().date()
	expired = StoreSubscription.objects.filter(status='active', end_date__lt=today)
	count = 0
	for subscription in expired:
		subscription.status = 'expired'
		subscription.save()
		count += 1
	return f'{count} abonnement(s) expiré(s)'


# Le client n'a ni confirmé ni signalé de problème 48 h après la livraison : le commerce (et le livreur) sont payés.
AUTO_RELEASE_AFTER = timedelta(hours=48)


def release_unconfirmed_payouts():
	"""Verse la part du commerce et du livreur des commandes livrées depuis 48 h sans confirmation du client.

	Rattrape aussi les commandes dont la réception a été confirmée sans déclencher le versement.
	Les versements restent idempotents : une commande déjà versée ou en cours n'est jamais repayée.
	"""
	from django.db.models.functions import Coalesce
	from orders.models import Order
	from payments.models import Payment
	from payments.store_payout_service import release_store_payment

	limit = timezone.now() - AUTO_RELEASE_AFTER
	orders = (
		Order.objects.filter(status='delivered', is_b2b=False, payment__status__in=('success', 'completed'))
		.annotate(done_at=Coalesce('delivery__delivered_at', 'delivered_at', 'updated_at'))
		.filter(done_at__lte=limit, client_problem_reported_at__isnull=True)
		# Remise prouvée par le code PIN du client (ou réception confirmée par le client) : une simple
		# « signature » photographiée par le livreur ne suffit pas à payer sans l'accord du client.
		.filter(Q(delivery__code_verified=True) | Q(delivery__proof__client_received_status=True))
		.exclude(store_payout__status__in=('processing', 'paid', 'skipped', 'failed'))
		.select_related('delivery', 'store')
		.distinct()[:50]
	)
	stores = drivers = 0
	for order in orders:
		try:
			payout = release_store_payment(order.pk)
			if payout is not None and payout.status in ('processing', 'paid', 'pending'):
				stores += 1
			if order.delivery.delivery_agent_id:
				from payments.services import PaymentService
				result = PaymentService.payout_delivery_agent(order.delivery)
				if result.get('success') and not result.get('skipped') and not result.get('already_processed'):
					drivers += 1
		except Exception:
			logger.exception('Versement automatique impossible pour la commande %s', order.order_number)
	return f'{stores} versement(s) commerce et {drivers} versement(s) livreur après 48 h sans confirmation'


JOBS = (
	('livraisons', timedelta(minutes=2), advance_deliveries),
	('paiements_en_ligne', timedelta(minutes=2), check_online_payments),
	('commandes_abandonnees', timedelta(hours=1), cancel_abandoned_orders),
	('abonnements_expires', timedelta(hours=12), expire_subscriptions),
	('versements_sans_confirmation', timedelta(hours=1), release_unconfirmed_payouts),
)


def run_due_jobs():
	"""Lance chaque tâche dont l'heure est venue. Renvoie {nom: résultat} pour les tâches lancées."""
	done = {}
	for name, every, job in JOBS:
		if not _claim(name, every):
			continue
		try:
			message, ok = job(), True
		except Exception as exc:
			logger.exception('Tâche automatique %s en échec', name)
			message, ok = f'Échec : {exc}', False
		_record(name, ok, message)
		done[name] = message
	return done
