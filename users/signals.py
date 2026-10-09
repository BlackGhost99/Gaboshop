"""Chaque compte livreur a son profil livreur, quelle que soit la façon dont il a été créé
(inscription, ajout par l'admin, console Django). Sans ce profil, le tableau de bord du livreur
ne s'ouvrait pas et le livreur ne recevait aucune course."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import LivreurProfile, User


@receiver(post_save, sender=User)
def ensure_courier_profile(sender, instance, raw=False, **kwargs):
    if raw or instance.user_type != 'delivery_agent':
        return
    LivreurProfile.objects.get_or_create(user=instance)
