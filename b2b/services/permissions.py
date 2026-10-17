"""
Services de permissions B2B
"""


def can_access_b2b(user):
	"""
	Vérifie si un utilisateur peut accéder au B2B
	
	Règles:
	- Uniquement StoreUser (user_type='store_manager')
	- Le magasin doit avoir un plan Pro ou Business (seuls les plans Pro/Business peuvent acheter en B2B)
	- Un magasin peut être à la fois B2B (vendeur) et B2C (acheteur)
	
	Args:
		user: Instance de User
	
	Returns:
		bool: True si l'utilisateur peut accéder au B2B
	"""
	import logging
	logger = logging.getLogger(__name__)
	
	if not user or not user.is_authenticated:
		logger.debug(f"can_access_b2b: User non authentifié - {user}")
		return False
	
	# Seuls les store_managers peuvent accéder au B2B
	if user.user_type != 'store_manager':
		logger.debug(f"can_access_b2b: User type incorrect - {user.user_type}")
		return False
	
	# Vérifier que le user a un store actif
	from stores.models import Store
	store = Store.objects.filter(manager=user, is_active=True).first()
	
	if not store:
		logger.debug(f"can_access_b2b: Aucun magasin actif trouvé pour user {user.id}")
		return False
	
	logger.debug(f"can_access_b2b: Store trouvé - ID: {store.id}, is_b2b: {store.is_b2b}, is_b2c: {store.is_b2c}")
	
	# Vérifier le plan de souscription
	from payments.subscription_check import SubscriptionChecker
	from b2b.models import B2BSubscriptionPlan
	plan = SubscriptionChecker.get_current_plan(store)
	
	if not plan:
		logger.warning(f"can_access_b2b: Aucun plan trouvé pour store {store.id}")
		return False
	
	# Si c'est un plan B2B, vérifier que ce n'est pas Free
	if isinstance(plan, B2BSubscriptionPlan):
		if plan.plan_type == 'free':
			logger.debug(f"can_access_b2b: Plan B2B Free - accès refusé pour approvisionnement")
			return False
		logger.debug(f"can_access_b2b: Plan B2B {plan.name} (plan_type: {plan.plan_type}) - accès autorisé")
		return True
	
	# Pour les plans B2C, vérifier can_access_b2b
	logger.debug(f"can_access_b2b: Plan trouvé - {plan.name} (plan_type: {plan.plan_type}), can_access_b2b: {getattr(plan, 'can_access_b2b', False)}")
	
	if not getattr(plan, 'can_access_b2b', False):
		logger.debug(f"can_access_b2b: Plan {plan.name} n'a pas can_access_b2b=True")
		return False
	
	logger.debug(f"can_access_b2b: Accès B2B autorisé pour store {store.id}")
	return True


def can_purchase_from_wholesaler(buyer_store, wholesaler_store):
	"""
	Vérifie si un magasin peut acheter d'un grossiste
	
	Règles:
	- Le magasin acheteur doit avoir le plan business (can_access_b2b)
	- Le grossiste doit être B2B (is_b2b=True)
	- Un grossiste ne peut pas s'acheter lui-même
	- Le profil B2B du grossiste doit être actif
	
	Args:
		buyer_store: Instance de Store (magasin acheteur)
		wholesaler_store: Instance de Store (grossiste)
	
	Returns:
		tuple: (bool, str) - (autorisé, message d'erreur)
	"""
	if not buyer_store or not wholesaler_store:
		return False, "Magasin invalide"

	# Prix pro et commandes B2B réservés aux commerces validés par Gaboshop (pas aux faux commerces).
	if not getattr(buyer_store, 'is_verified', True):
		return False, "Votre commerce doit d'abord être validé par Gaboshop pour acheter en gros"
	
	# Vérifier que le magasin acheteur a accès au B2B (plan business)
	from payments.subscription_check import SubscriptionChecker
	from b2b.models import B2BSubscriptionPlan
	plan = SubscriptionChecker.get_current_plan(buyer_store)
	
	if not plan:
		return False, "Un forfait Pro ou Business est requis pour accéder au B2B"
	
	# Si le store est B2B (grossiste), autoriser l'accès
	if buyer_store.is_b2b:
		pass  # Autoriser
	# Si c'est un plan B2B, autoriser l'accès
	elif isinstance(plan, B2BSubscriptionPlan):
		pass  # Autoriser
	# Pour les plans B2C, vérifier can_access_b2b
	elif not getattr(plan, 'can_access_b2b', False):
		return False, "Un forfait Pro ou Business est requis pour accéder au B2B"
	
	# Le grossiste doit être B2B
	if not wholesaler_store.is_b2b:
		return False, "Ce magasin n'est pas un grossiste"
	
	# Un grossiste ne peut pas s'acheter lui-même
	if buyer_store.id == wholesaler_store.id:
		return False, "Vous ne pouvez pas acheter de votre propre magasin"
	
	# Vérifier que le profil B2B est actif
	try:
		b2b_profile = wholesaler_store.b2b_profile
		if not b2b_profile.is_active:
			return False, "Le profil B2B de ce grossiste n'est pas actif"
	except AttributeError:
		# Pas de profil B2B
		return False, "Ce magasin n'a pas de profil B2B"
	
	# Vérifier la visibilité
	if not b2b_profile.visible_to_all:
		# TODO: Implémenter la logique d'accès restreint si nécessaire
		pass
	
	return True, ""


def can_purchase_from_self(buyer_store, wholesaler):
	"""
	Un store ne peut pas acheter chez lui-même
	
	Args:
		buyer_store: Instance de Store (magasin acheteur)
		wholesaler: Instance de Store (grossiste)
	
	Returns:
		tuple: (bool, str) - (autorisé, message d'erreur)
	"""
	if buyer_store.id == wholesaler.id:
		return False, "Vous ne pouvez pas commander chez votre propre magasin"
	return True, None


def must_be_b2c_store(store):
	"""
	Seuls les stores B2C peuvent passer des commandes B2B
	
	Args:
		store: Instance de Store
	
	Returns:
		tuple: (bool, str) - (autorisé, message d'erreur)
	"""
	if not store or not store.is_b2c:
		return False, ("Un grossiste vend aux commerces mais ne commande pas chez un autre grossiste : "
		               "l'approvisionnement est réservé aux commerces de détail.")
	return True, None


def check_b2b_buyer_quotas(buyer_store):
	"""
	Vérifie les quotas B2B pour un store buyer (B2C qui achète)
	
	Args:
		buyer_store: Instance de Store (magasin B2C)
	
	Returns:
		tuple: (bool, dict) - (autorisé, dict avec détails des quotas)
	"""
	from payments.subscription_check import SubscriptionChecker
	plan = SubscriptionChecker.get_current_plan(buyer_store)
	
	if not plan:
		return False, {'error': 'Aucun plan actif'}
	
	quotas = {
		'max_suppliers': getattr(plan, 'max_b2b_suppliers', None),
		'max_monthly_orders': getattr(plan, 'max_b2b_monthly_orders', None),
		'current_suppliers': None,
		'current_monthly_orders': None,
	}
	
	# Compter les fournisseurs uniques (grossistes) avec lesquels le store a commandé
	from orders.models import Order
	from django.utils import timezone
	from datetime import timedelta
	
	# Fournisseurs uniques (30 derniers jours)
	thirty_days_ago = timezone.now() - timedelta(days=30)
	unique_suppliers = Order.objects.filter(
		source_store=buyer_store,
		is_b2b=True,
		created_at__gte=thirty_days_ago
	).values_list('store_id', flat=True).distinct().count()
	
	quotas['current_suppliers'] = unique_suppliers
	
	# Commandes B2B du mois en cours
	start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
	monthly_orders_count = Order.objects.filter(
		source_store=buyer_store,
		is_b2b=True,
		created_at__gte=start_of_month
	).count()
	
	quotas['current_monthly_orders'] = monthly_orders_count
	
	# Vérifier les limites
	if quotas['max_suppliers'] is not None and unique_suppliers >= quotas['max_suppliers']:
		return False, {
			'error': f'Limite de {quotas["max_suppliers"]} fournisseurs atteinte',
			**quotas
		}
	
	if quotas['max_monthly_orders'] is not None and monthly_orders_count >= quotas['max_monthly_orders']:
		return False, {
			'error': f'Limite de {quotas["max_monthly_orders"]} commandes B2B/mois atteinte',
			**quotas
		}
	
	return True, quotas


BUYER_CAP_MESSAGE = "Ce grossiste ne peut plus accepter de nouveaux commerces clients pour le moment."


def recent_buyer_ids(wholesaler_store, days=30):
	"""Identifiants des commerces acheteurs distincts d'un grossiste sur les derniers jours (commandes annulées exclues)."""
	from orders.models import Order
	from django.utils import timezone
	from datetime import timedelta
	since = timezone.now() - timedelta(days=days)
	return set(
		Order.objects.filter(
			store=wholesaler_store, is_b2b=True, source_store__isnull=False, created_at__gte=since,
		).exclude(status='cancelled').values_list('source_store_id', flat=True).distinct()
	)


def check_buyer_plan_limits(buyer_store, wholesaler_store):
	"""
	Limites d'achat en gros du forfait d'un commerce acheteur : nombre de grossistes différents (30 jours) et
	commandes B2B du mois. Un grossiste déjà fournisseur reste toujours servi pour le plafond de fournisseurs.
	Sans limite (null) ou pour un grossiste acheteur, tout passe.

	Returns:
		tuple: (bool, str) - (autorisé, message pour le commerce acheteur)
	"""
	from datetime import timedelta
	from django.utils import timezone
	from orders.models import Order
	from payments.plan_features import plan_for_sale
	from b2b.models import B2BSubscriptionPlan
	plan = buyer_store.get_current_plan() if buyer_store is not None else None
	if plan is None or isinstance(plan, B2BSubscriptionPlan) or buyer_store.is_b2b:
		return True, ''
	max_suppliers = getattr(plan, 'max_b2b_suppliers', None)
	max_orders = getattr(plan, 'max_b2b_monthly_orders', None)
	if not max_suppliers and not max_orders:
		return True, ''
	now = timezone.now()
	orders = Order.objects.filter(source_store=buyer_store, is_b2b=True).exclude(status__in=('cancelled', 'refunded'))

	def lifted_by(accepts):
		target = plan_for_sale(plan, accepts)
		if target is None:
			return "Aucun forfait en vente ne lève cette limite pour le moment."
		return f"Passez à {target.name} dans « Mon forfait » pour la lever."

	if max_suppliers:
		suppliers = set(orders.filter(created_at__gte=now - timedelta(days=30)).values_list('store_id', flat=True))
		if wholesaler_store.id not in suppliers and len(suppliers) >= max_suppliers:
			return False, (f"Votre forfait {plan.name} permet de commander chez {max_suppliers} grossistes différents "
			               f"sur 30 jours, et vous les avez atteints. Vous pouvez encore commander chez vos fournisseurs habituels. "
			               + lifted_by(lambda c: c.can_access_b2b and (c.max_b2b_suppliers is None or c.max_b2b_suppliers > max_suppliers)))
	if max_orders:
		month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
		if orders.filter(created_at__gte=month_start).count() >= max_orders:
			return False, (f"Votre forfait {plan.name} permet {max_orders} commandes en gros par mois, et vous les avez "
			               f"atteintes. Elles reviennent le 1er du mois prochain. "
			               + lifted_by(lambda c: c.can_access_b2b and (c.max_b2b_monthly_orders is None or c.max_b2b_monthly_orders > max_orders)))
	return True, ''


def check_b2c_buyer_quota(wholesaler_store, buyer_store=None):
	"""
	Plafond de commerces clients du forfait grossiste (max_b2c_buyers, commerces distincts sur 30 jours).

	Un commerce déjà client sur la période reste toujours servi ; seul un nouveau commerce est refusé
	quand le plafond est atteint. Sans plafond (forfait illimité ou forfait de commerce), tout passe.

	Returns:
		tuple: (bool, dict) - (autorisé, détails : max_buyers, current_buyers, message)
	"""
	from b2b.models import B2BSubscriptionPlan
	plan = wholesaler_store.get_current_plan() if wholesaler_store is not None else None
	max_buyers = getattr(plan, 'max_b2c_buyers', None) if isinstance(plan, B2BSubscriptionPlan) else None
	details = {'max_buyers': max_buyers, 'current_buyers': None, 'message': ''}
	if not max_buyers:
		return True, details
	buyers = recent_buyer_ids(wholesaler_store)
	details['current_buyers'] = len(buyers)
	if buyer_store is not None and buyer_store.id in buyers:
		return True, details
	if len(buyers) < max_buyers:
		return True, details
	details['message'] = BUYER_CAP_MESSAGE
	return False, details


def notify_buyer_cap_reached(wholesaler_store, buyer_store, details):
	"""Prévient le grossiste (une fois par jour) qu'un nouveau commerce a été refusé, avec le forfait qui lève le plafond."""
	from django.utils import timezone
	from datetime import timedelta
	from notifications.models import Notification
	from notifications.service import NotificationService
	from notifications import messages
	from payments.plan_features import plan_for_sale
	manager = getattr(wholesaler_store, 'manager', None)
	if manager is None:
		return None
	recent = Notification.objects.filter(
		user=manager, metadata__reason_code='b2c_buyer_cap', created_at__gte=timezone.now() - timedelta(days=1))
	if recent.exists():
		return None
	plan = wholesaler_store.get_current_plan()
	cap = details.get('max_buyers') or 0
	target = plan_for_sale(plan, lambda candidate: not candidate.max_b2c_buyers or candidate.max_b2c_buyers > cap)
	message = messages.b2c_buyer_cap_for_wholesaler(buyer_store, plan, cap, target)
	return NotificationService.notify_user(
		manager, message, notif_type='warning', metadata={'reason_code': 'b2c_buyer_cap', 'buyer_store_id': buyer_store.id})


def check_b2b_wholesaler_quotas(wholesaler_store):
	"""
	Vérifie les quotas B2B pour un grossiste
	
	Args:
		wholesaler_store: Instance de Store (grossiste B2B)
	
	Returns:
		tuple: (bool, dict) - (autorisé, dict avec détails des quotas)
	"""
	from b2b.models import B2BStoreSubscription
	from django.utils import timezone
	from datetime import timedelta
	
	# Récupérer le plan B2B du grossiste
	b2b_subscription = getattr(wholesaler_store, 'b2b_subscription', None)
	if not b2b_subscription or not b2b_subscription.plan:
		return False, {'error': 'Aucun plan B2B actif'}
	
	plan = b2b_subscription.plan
	
	quotas = {
		'max_products': getattr(plan, 'max_b2b_products', None),
		'max_buyers': getattr(plan, 'max_b2c_buyers', None),
		'current_products': None,
		'current_buyers': None,
	}
	
	# Compter les produits B2B actifs
	from b2b.models import B2BProductPricing
	current_products = B2BProductPricing.objects.filter(
		b2b_store=wholesaler_store,
		is_active=True
	).count()
	
	quotas['current_products'] = current_products
	
	# Compter les buyers uniques (30 derniers jours)
	unique_buyers = len(recent_buyer_ids(wholesaler_store))
	
	quotas['current_buyers'] = unique_buyers
	
	# Vérifier les limites
	if quotas['max_products'] is not None and current_products >= quotas['max_products']:
		return False, {
			'error': f'Limite de {quotas["max_products"]} produits B2B atteinte',
			**quotas
		}
	
	if quotas['max_buyers'] is not None and unique_buyers >= quotas['max_buyers']:
		return False, {
			'error': f'Limite de {quotas["max_buyers"]} clients B2C atteinte',
			**quotas
		}
	
	return True, quotas

