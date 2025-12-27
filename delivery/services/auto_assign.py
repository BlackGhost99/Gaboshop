"""Service d'assignation automatique de livraisons.
"""
from django.db import transaction
from django.utils import timezone
import logging

from delivery.models import Delivery, DeliveryProfile
from users.models import User
from delivery.services import DeliveryService

logger = logging.getLogger(__name__)


@transaction.atomic
def auto_assign_delivery(order):
    """Assigne automatiquement un livreur disponible à la commande prête.

    Retourne la Delivery assignée ou None si aucun livreur disponible.
    """
    try:
        # Sécurité : verrou sur la livraison liée (si existante)
        try:
            delivery = Delivery.objects.select_for_update().get(order=order)
        except Delivery.DoesNotExist:
            delivery, _ = Delivery.objects.get_or_create(order=order)

        # Si déjà assignée, on sort
        if delivery.delivery_agent is not None:
            return delivery

        # Cherche un profil de livreur disponible
        profile = (
            DeliveryProfile.objects
            .select_for_update()
            .filter(status='available')
            .select_related('user')
            .first()
        )

        if not profile:
            logger.info(f"auto_assign: pas de livreur disponible pour order {order.id}")
            return None

        # Assigner via le service existant
        delivery = DeliveryService.assign_delivery_agent(order, profile.user)

        # Marquer le profil occupé
        try:
            profile.status = 'busy'
            profile.save()
        except Exception:
            # Pas critique: on continue même si on ne peut pas marquer le profil
            logger.exception('Impossible de mettre à jour le statut du profil livreur')

        # Marquer que c'est une assignation automatique
        delivery.is_auto_assigned = True
        delivery.assigned_at = delivery.assigned_at or timezone.now()
        delivery.save()

        logger.info(f"Auto-assign: livraison {delivery.id} → livreur {profile.user.id}")
        return delivery

    except Exception:
        logger.exception('Erreur auto_assign_delivery')
        return None
