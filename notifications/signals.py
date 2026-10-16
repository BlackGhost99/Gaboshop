"""Chaque notification créée part aussi en alerte sur les appareils de la personne (voir notifications/push.py)."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Notification
from . import push


@receiver(post_save, sender=Notification)
def push_new_notification(sender, instance, created, **kwargs):
    if created and not kwargs.get('raw') and not getattr(instance, '_skip_push', False):
        push.schedule_notification(instance)
