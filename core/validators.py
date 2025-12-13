"""
Validateurs pour les transitions de statut et les règles métier
"""
from decimal import Decimal
from math import radians, cos, sin, asin, sqrt
from django.utils import timezone
from datetime import datetime
from .exceptions import BusinessValidationError


def validate_not_null(value, name: str = 'value'):
    """Lève BusinessValidationError si value est None"""
    if value is None:
        raise BusinessValidationError(f"{name} ne peut pas être null")


def ensure_timezone_aware(dt):
    """Retourne un datetime timezone-aware; si dt est naive, on le rend aware avec le timezone courant."""
    if dt is None:
        return None
    if not isinstance(dt, datetime):
        return dt
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, timezone.get_current_timezone())
    return dt

# Transitions valides pour les commandes
ORDER_STATUS_TRANSITIONS = {
    'created': ['pending_payment', 'cancelled'],
    'pending_payment': ['paid', 'cancelled'],
    'paid': ['confirmed', 'cancelled'],
    'confirmed': ['preparing', 'cancelled'],
    'preparing': ['ready', 'cancelled'],
    'ready': ['assigned', 'cancelled'],
    'assigned': ['in_transit', 'cancelled'],
    'in_transit': ['delivered', 'failed'],
    'delivered': [],  # État final
    'cancelled': [],  # État final
    'refunded': [],  # État final
    'failed': ['ready', 'cancelled'],  # Peut être réassignée
}

# Transitions valides pour les livraisons
DELIVERY_STATUS_TRANSITIONS = {
    'waiting': ['pending', 'cancelled'],
    'pending': ['assigned', 'accepted', 'rejected'],  # 'accepted' pour compatibilité avec les données existantes
    'assigned': ['accepted', 'rejected'],
    'accepted': ['picked_up', 'delivered', 'rejected'],  # Peut aller directement à delivered si preuve disponible
    'picked_up': ['in_transit'],
    'in_transit': ['delivered', 'failed'],
    'delivered': [],  # État final
    'failed': ['waiting', 'cancelled'],  # Peut être reasignée ou annulée
    'cancelled': [],  # État final
    'rejected': ['waiting'],  # Revient en attente d'assignation
}

# Permissions par rôle pour changer de statut
ROLE_PERMISSIONS = {
    'admin': {
        'order': ['created', 'pending_payment', 'paid', 'confirmed', 'preparing', 'ready', 'assigned', 'in_transit', 'delivered', 'cancelled', 'refunded', 'failed'],
        'delivery': ['waiting', 'pending', 'assigned', 'accepted', 'picked_up', 'in_transit', 'delivered', 'cancelled', 'failed'],
    },
    'store_manager': {
        'order': ['preparing', 'ready', 'cancelled'],  # Peut préparer et marquer prête
        'delivery': [],  # Pas d'accès direct
    },
    'client': {
        'order': ['cancelled'],  # Peut annuler avant confirmation
        'delivery': [],  # Pas d'accès
    },
    'delivery_agent': {
        'order': [],  # Pas d'accès direct
        'delivery': ['accepted', 'picked_up', 'in_transit', 'delivered'],  # Peut accepter et livrer
    },
}


def is_valid_order_transition(current_status, new_status):
    """
    Vérifie si une transition de statut de commande est valide
    
    Args:
        current_status: Statut actuel
        new_status: Nouveau statut
        
    Returns:
        bool: True si valide, False sinon
    """
    if current_status not in ORDER_STATUS_TRANSITIONS:
        return False
    
    return new_status in ORDER_STATUS_TRANSITIONS[current_status]


def is_valid_delivery_transition(current_status, new_status):
    """
    Vérifie si une transition de statut de livraison est valide
    
    Args:
        current_status: Statut actuel
        new_status: Nouveau statut
        
    Returns:
        bool: True si valide, False sinon
    """
    if current_status not in DELIVERY_STATUS_TRANSITIONS:
        return False
    
    return new_status in DELIVERY_STATUS_TRANSITIONS[current_status]


def can_user_change_order_status(user, current_status, new_status):
    """
    Vérifie si un utilisateur peut changer le statut d'une commande
    
    Args:
        user: User object
        current_status: Statut actuel
        new_status: Nouveau statut
        
    Returns:
        tuple: (is_allowed, error_message)
    """
    # Admin peut tout faire
    if user.is_admin():
        if is_valid_order_transition(current_status, new_status):
            return True, None
        else:
            return False, f"Transition invalide: {current_status} → {new_status}"
    
    # Récupérer le rôle de l'utilisateur
    user_role = user.user_type
    
    if user_role not in ROLE_PERMISSIONS:
        return False, f"Rôle non reconnu: {user_role}"
    
    # Vérifier que le nouvel état est autorisé pour ce rôle
    allowed_statuses = ROLE_PERMISSIONS[user_role]['order']
    
    if new_status not in allowed_statuses:
        return False, f"Vous ne pouvez pas changer vers le statut: {new_status}"
    
    # Vérifier que la transition est valide
    if not is_valid_order_transition(current_status, new_status):
        return False, f"Transition invalide: {current_status} → {new_status}"
    
    return True, None


def can_user_change_delivery_status(user, current_status, new_status):
    """
    Vérifie si un utilisateur peut changer le statut d'une livraison
    
    Args:
        user: User object
        current_status: Statut actuel
        new_status: Nouveau statut
        
    Returns:
        tuple: (is_allowed, error_message)
    """
    # Admin peut tout faire
    if user.is_admin():
        if is_valid_delivery_transition(current_status, new_status):
            return True, None
        else:
            return False, f"Transition invalide: {current_status} → {new_status}"
    
    # Récupérer le rôle de l'utilisateur
    user_role = user.user_type
    
    if user_role not in ROLE_PERMISSIONS:
        return False, f"Rôle non reconnu: {user_role}"
    
    # Vérifier que le nouvel état est autorisé pour ce rôle
    allowed_statuses = ROLE_PERMISSIONS[user_role]['delivery']
    
    if new_status not in allowed_statuses:
        return False, f"Vous ne pouvez pas changer vers le statut: {new_status}"
    
    # Vérifier que la transition est valide
    if not is_valid_delivery_transition(current_status, new_status):
        return False, f"Transition invalide: {current_status} → {new_status}"
    
    return True, None


def get_valid_next_statuses(current_status, is_order=True):
    """
    Retourne les statuts possibles suivants
    
    Args:
        current_status: Statut actuel
        is_order: True si c'est une commande, False si c'est une livraison
        
    Returns:
        list: Liste des statuts possibles
    """
    transitions = ORDER_STATUS_TRANSITIONS if is_order else DELIVERY_STATUS_TRANSITIONS
    
    if current_status not in transitions:
        return []
    
    return transitions[current_status]


def calculate_gps_distance(lat1, lon1, lat2, lon2):
	"""
	Calcule la distance entre deux points GPS en mètres
	Utilise la formule de Haversine
	
	Args:
		lat1, lon1: Coordonnées du point 1
		lat2, lon2: Coordonnées du point 2
	
	Returns:
		Distance en mètres
	"""
	# Convertir en float si Decimal
	lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
	
	# Rayon de la Terre en km
	R = 6371.0
	
	# Convertir en radians
	lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
	
	# Différences
	dlat = lat2 - lat1
	dlon = lon2 - lon1
	
	# Formule de Haversine
	a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
	c = 2 * asin(sqrt(a))
	
	# Distance en mètres
	distance_meters = R * c * 1000
	
	return round(distance_meters, 2)


def validate_delivery_proof(delivery, proof_data):
	"""
	Valide une preuve de livraison
	
	Args:
		delivery: Instance Delivery
		proof_data: Dict avec id_card_photo, latitude, longitude, signature/pin
	
	Returns:
		tuple: (is_valid, errors_dict)
	"""
	errors = {}
	
	# 1. Photo pièce d'identité OBLIGATOIRE (car client peut venir chercher)
	if not proof_data.get('id_card_photo'):
		errors['id_card_photo'] = "La photo de la pièce d'identité du client est obligatoire"
	
	# Note: package_photo est optionnelle, pas vérifiée
	
	# 2. Coordonnées GPS obligatoires
	latitude = proof_data.get('latitude') or proof_data.get('proof_latitude')
	longitude = proof_data.get('longitude') or proof_data.get('proof_longitude')
	
	if not latitude or not longitude:
		errors['gps'] = "Les coordonnées GPS sont obligatoires"
	else:
		try:
			lat = Decimal(str(latitude))
			lon = Decimal(str(longitude))
			
			# Vérifier les limites GPS valides
			if not (-90 <= lat <= 90):
				errors['latitude'] = "Latitude invalide (doit être entre -90 et 90)"
			if not (-180 <= lon <= 180):
				errors['longitude'] = "Longitude invalide (doit être entre -180 et 180)"
			
			# Vérifier la distance avec l'adresse de livraison
			if delivery.delivery_lat and delivery.delivery_lng and not errors:
				distance = calculate_gps_distance(
					lat, lon,
					delivery.delivery_lat, delivery.delivery_lng
				)
				
				# Tolérance: 500 mètres (peut être ajusté)
				if distance > 500:
					errors['gps_distance'] = f"Position GPS trop éloignée de l'adresse de livraison ({distance:.0f}m)"
		except (ValueError, TypeError, Exception) as e:
			errors['gps'] = f"Coordonnées GPS invalides: {str(e)}"
	
	# 3. Signature OU Code PIN requis
	has_signature = bool(proof_data.get('signature') or proof_data.get('client_signature'))
	has_pin = bool(proof_data.get('pin_code'))
	pin_verified = proof_data.get('pin_verified', False)
	
	if not has_signature and not has_pin:
		errors['verification'] = "La signature du client ou le code PIN est requis"
	
	# 4. Si PIN fourni, vérifier qu'il correspond
	if has_pin and not pin_verified:
		provided_pin = proof_data.get('pin_code', '').strip()
		expected_pin = delivery.delivery_code.strip()
		
		if provided_pin != expected_pin:
			errors['pin_code'] = "Code PIN incorrect"
	
	is_valid = len(errors) == 0
	return is_valid, errors


def can_mark_as_delivered(delivery):
	"""
	Vérifie si une livraison peut être marquée comme 'delivered'
	
	Args:
		delivery: Instance Delivery
	
	Returns:
		tuple: (can_deliver, reason)
	"""
	# 1. Statut doit être 'in_transit' ou 'picked_up' ou 'accepted' (si preuve disponible)
	if delivery.status not in ['in_transit', 'picked_up', 'accepted']:
		return False, f"La livraison doit être en transit. Statut actuel: {delivery.get_status_display()}"
	
	# 2. Doit avoir un livreur assigné
	if not delivery.delivery_agent:
		return False, "Aucun livreur assigné à cette livraison"
	
	# 3. Vérifier si une preuve existe déjà
	from delivery.models import DeliveryProof
	try:
		proof = DeliveryProof.objects.get(delivery=delivery)
		if not proof.is_valid:
			return False, "La preuve de livraison est incomplète"
	except DeliveryProof.DoesNotExist:
		# Vérifier les anciens champs pour rétrocompatibilité
		if not delivery.delivery_proof_photo:
			return False, "La photo de livraison est requise"
		if not delivery.proof_latitude or not delivery.proof_longitude:
			return False, "Les coordonnées GPS sont requises"
		if not delivery.client_signature and not delivery.code_verified:
			return False, "La signature ou le code PIN vérifié est requis"
	
	return True, "OK"
