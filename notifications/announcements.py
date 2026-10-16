"""Annonces de l'administration : un message envoyé d'un coup à tous les clients, commerces ou livreurs."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from users.models import User

from . import push
from .models import Announcement, Notification, PushSubscription

BATCH = 500
USER_TYPES = {
    'clients': ['client'],
    'stores': ['store_manager'],
    'drivers': ['delivery_agent'],
    'everyone': ['client', 'store_manager', 'delivery_agent'],
}
AUDIENCE_LABELS = {
    'clients': 'Tous les clients',
    'stores': 'Tous les commerces',
    'drivers': 'Tous les livreurs',
    'everyone': 'Tout le monde',
    'me': 'Moi seul (essai)',
}


def audience_users(audience, sender=None):
    """Personnes qui recevront l'annonce : comptes actifs du groupe, sauf ceux qui ont coupé les annonces."""
    if audience == 'me':
        return User.objects.filter(pk=getattr(sender, 'pk', None))
    return (User.objects.filter(user_type__in=USER_TYPES.get(audience, []), is_active=True)
            .exclude(notification_preferences__announcements=False))


def audience_counts():
    """Pour l'écran d'envoi : combien de personnes, et combien ont les alertes sur leur téléphone."""
    counts = {}
    for audience in USER_TYPES:
        users = audience_users(audience)
        counts[audience] = {
            'recipients': users.count(),
            'with_alerts': PushSubscription.objects.filter(user__in=users, is_active=True).values('user').distinct().count(),
        }
    return counts


def find_duplicate(title, body, audience, within=timedelta(minutes=2)):
    """Même message au même groupe dans les 2 dernières minutes : presque sûrement un double clic."""
    return Announcement.objects.filter(
        title=title, body=body, audience=audience, created_at__gte=timezone.now() - within,
    ).first()


@transaction.atomic
def send_announcement(announcement, sender=None):
    """Crée la notification de chaque destinataire, puis lance l'alerte téléphone (ou la repousse à 7 h la nuit)."""
    batch, total = [], 0
    for user_id in audience_users(announcement.audience, sender).values_list('id', flat=True).iterator(chunk_size=1000):
        batch.append(Notification(
            user_id=user_id, title=announcement.title, body=announcement.body, notif_type='announcement',
            link=announcement.link, action_label=announcement.action_label, announcement=announcement,
            metadata={'level': 'info', 'source': 'announcement'},
        ))
        if len(batch) >= BATCH:
            Notification.objects.bulk_create(batch)
            total += len(batch)
            batch = []
    if batch:
        Notification.objects.bulk_create(batch)
        total += len(batch)
    announcement.sent_at = timezone.now()
    announcement.recipients_count = total
    announcement.save(update_fields=['sent_at', 'recipients_count'])
    announcement.push_mode = push.schedule_announcement(announcement)
    return announcement
