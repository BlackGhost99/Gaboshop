"""
Services de permissions B2B
"""


def can_access_b2b(user):
	"""
	Vérifie si un utilisateur peut accéder au B2B
	
	Règles:
	- Uniquement StoreUser (user_type='store_manager')
	- Le magasin doit avoir un plan Business (seuls les Business peuvent acheter en B2B)
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
	
	# Vérifier que le magasin acheteur a accès au B2B (plan business)
	from payments.subscription_check import SubscriptionChecker
	from b2b.models import B2BSubscriptionPlan
	plan = SubscriptionChecker.get_current_plan(buyer_store)
	
	if not plan:
		return False, "Un forfait Business est requis pour accéder au B2B"
	
	# Si le store est B2B (grossiste), autoriser l'accès
	if buyer_store.is_b2b:
		pass  # Autoriser
	# Si c'est un plan B2B, autoriser l'accès
	elif isinstance(plan, B2BSubscriptionPlan):
		pass  # Autoriser
	# Pour les plans B2C, vérifier can_access_b2b
	elif not getattr(plan, 'can_access_b2b', False):
		return False, "Un forfait Business est requis pour accéder au B2B"
	
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
		return False, "Seuls les magasins B2C peuvent passer des commandes B2B"
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
	from orders.models import Order
	thirty_days_ago = timezone.now() - timedelta(days=30)
	unique_buyers = Order.objects.filter(
		store=wholesaler_store,
		is_b2b=True,
		source_store__isnull=False,
		created_at__gte=thirty_days_ago
	).values_list('source_store_id', flat=True).distinct().count()
	
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

