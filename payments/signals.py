"""
Signals pour le module payments
Gestion automatique de l'expiration des souscriptions
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import StoreSubscription, SubscriptionPlan


@receiver(pre_save, sender=StoreSubscription)
def check_expiry_before_save(sender, instance, **kwargs):
    """
    Vérifie si l'abonnement est expiré avant de sauvegarder
    """
    if instance.pk and instance.status == 'active':
        # Vérifier si la date d'expiration est passée
        if instance.end_date < timezone.now().date():
            # Marquer comme expiré
            instance.status = 'expired'


@receiver(post_save, sender=StoreSubscription)
def handle_subscription_expiry(sender, instance, created, **kwargs):
    """
    Quand une souscription expire, créer automatiquement une souscription Free
    """
    # Si la souscription vient d'être marquée comme expirée
    if not created and instance.status == 'expired':
        # Vérifier qu'il n'y a pas déjà une souscription active Free
        active_free = StoreSubscription.objects.filter(
            store=instance.store,
            status='active',
            plan__plan_type='free'
        ).exists()
        
        if not active_free:
            # Créer une nouvelle souscription Free
            try:
                free_plan = SubscriptionPlan.objects.get(plan_type='free')
                
                # Créer souscription Free (valable "pour toujours")
                StoreSubscription.objects.create(
                    store=instance.store,
                    plan=free_plan,
                    plan_name='Free',
                    monthly_fee=0,
                    status='active',
                    start_date=timezone.now().date(),
                    end_date=timezone.now().date() + timedelta(days=36500),  # ~100 ans
                    auto_renew=False
                )
                
                print(f"[Auto-downgrade] {instance.store.name} downgrade vers Free")
                
            except SubscriptionPlan.DoesNotExist:
                print(f"[ERREUR] Plan Free introuvable pour auto-downgrade de {instance.store.name}")
