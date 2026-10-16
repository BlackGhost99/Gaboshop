import hashlib

from django.db import models
from django.conf import settings
from orders.models import Order
from delivery.models import Delivery


class Announcement(models.Model):
    """Message envoyé par l'administration à un groupe d'utilisateurs (clients, commerces, livreurs)."""
    AUDIENCES = (
        ('clients', 'Tous les clients'),
        ('stores', 'Tous les commerces'),
        ('drivers', 'Tous les livreurs'),
        ('everyone', 'Tout le monde'),
        ('me', 'Moi seul (essai)'),
    )

    title = models.CharField(max_length=120)
    body = models.TextField(max_length=600)
    audience = models.CharField(max_length=20, choices=AUDIENCES, default='clients')
    link = models.CharField(max_length=200, blank=True, default='')
    action_label = models.CharField(max_length=40, blank=True, default='')
    send_push = models.BooleanField(default=True)
    urgent = models.BooleanField(default=False)  # alerte téléphone même la nuit
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='announcements')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    recipients_count = models.PositiveIntegerField(default=0)
    push_after = models.DateTimeField(null=True, blank=True)  # alerte téléphone repoussée au matin
    push_done = models.BooleanField(default=False)
    push_attempted = models.PositiveIntegerField(default=0)
    push_delivered = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_audience_display()})"


class Notification(models.Model):
    NOTIF_TYPES = (
        ('info', 'Info'),
        ('order', 'Order'),
        ('delivery', 'Delivery'),
        ('payment', 'Payment'),
        ('warning', 'Warning'),
        ('announcement', 'Announcement'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    body = models.TextField()
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES, default='info')
    is_read = models.BooleanField(default=False)

    # Liens optionnels
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')
    delivery = models.ForeignKey(Delivery, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')

    # Où mène la notification (chemin de l'application) et le texte du bouton : « Voir ma commande »
    link = models.CharField(max_length=200, blank=True, default='')
    action_label = models.CharField(max_length=40, blank=True, default='')
    announcement = models.ForeignKey(Announcement, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='notifications')

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notif_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.title} -> {self.user}"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.link:
            from .links import default_action
            self.link, label = default_action(self)
            if not self.action_label:
                self.action_label = label
        super().save(*args, **kwargs)


class PushSubscription(models.Model):
    """Un appareil qui accepte les alertes : navigateur (Web Push) ou, plus tard, application Android (FCM)."""
    KINDS = (('web', 'Navigateur'), ('fcm', 'Application Android'))

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='push_subscriptions')
    kind = models.CharField(max_length=10, choices=KINDS, default='web')
    endpoint = models.TextField()
    endpoint_hash = models.CharField(max_length=64, unique=True, editable=False)
    p256dh = models.CharField(max_length=255, blank=True, default='')
    auth = models.CharField(max_length=255, blank=True, default='')
    user_agent = models.CharField(max_length=300, blank=True, default='')
    is_active = models.BooleanField(default=True)
    failure_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_success_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'is_active'])]

    @staticmethod
    def hash_endpoint(endpoint):
        return hashlib.sha256(endpoint.encode('utf-8')).hexdigest()

    def save(self, *args, **kwargs):
        self.endpoint_hash = self.hash_endpoint(self.endpoint)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.kind} -> {self.user}"


class NotificationPreference(models.Model):
    """Réglages du client : il peut couper les annonces, jamais les alertes de ses commandes."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='notification_preferences')
    announcements = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)


class PushKeyPair(models.Model):
    """Clés VAPID de ce site (créées au premier besoin, jamais affichées) : elles signent les alertes envoyées."""
    public_key = models.CharField(max_length=200)
    private_key = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)
