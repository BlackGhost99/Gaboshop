from django.db import models
from django.conf import settings
from orders.models import Order
from delivery.models import Delivery


class Notification(models.Model):
    NOTIF_TYPES = (
        ('info', 'Info'),
        ('order', 'Order'),
        ('delivery', 'Delivery'),
        ('payment', 'Payment'),
        ('warning', 'Warning'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200)
    body = models.TextField()
    notif_type = models.CharField(max_length=20, choices=NOTIF_TYPES, default='info')
    is_read = models.BooleanField(default=False)

    # Liens optionnels
    order = models.ForeignKey(Order, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')
    delivery = models.ForeignKey(Delivery, null=True, blank=True, on_delete=models.CASCADE, related_name='notifications')

    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['notif_type', 'created_at']),
        ]

    def __str__(self):
        return f"{self.title} -> {self.user}"