"""
Services de permissions B2B
"""


def can_access_b2b(user):
	"""
	Vérifie si un utilisateur peut accéder au B2B
	
	Règles:
	- Uniquement StoreUser (user_type='store_manager')
	- Le magasin doit avoir is_b2c = True
	
	Args:
		user: Instance de User
	
	Returns:
		bool: True si l'utilisateur peut accéder au B2B
	"""
	if not user or not user.is_authenticated:
		return False
	
	# Seuls les store_managers peuvent accéder au B2B
	if user.user_type != 'store_manager':
		return False
	
	# Vérifier que le user a un store actif
	from stores.models import Store
	store = Store.objects.filter(manager=user, is_active=True).first()
	return bool(store)


def can_purchase_from_wholesaler(buyer_store, wholesaler_store):
	"""
	Vérifie si un magasin B2C peut acheter d'un grossiste
	
	Règles:
	- Le magasin acheteur doit être B2C (is_b2c=True)
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
	
	# Le magasin acheteur doit être B2C
	if not buyer_store.is_b2c:
		return False, "Votre magasin n'est pas configuré pour le B2C"
	
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

