"""Demandes d'assistance : chaque demande garde le niveau de support du forfait au moment où elle est ouverte."""
from django.conf import settings
from django.db import models

PRIORITY_DEDICATED = 'dedie'
PRIORITY_PRIORITY = 'prioritaire'
PRIORITY_STANDARD = 'standard'

# Plus le rang est petit, plus la demande passe tôt : ligne dédiée, puis prioritaire, puis standard.
PRIORITY_RANKS = {PRIORITY_DEDICATED: 0, PRIORITY_PRIORITY: 1, PRIORITY_STANDARD: 2}


class SupportTicket(models.Model):
    CATEGORIES = (
        ('order', 'Commande'),
        ('payment', 'Paiement'),
        ('delivery', 'Livraison'),
        ('plan', 'Forfait'),
        ('account', 'Compte'),
        ('technical', 'Problème technique'),
        ('other', 'Autre'),
    )
    STATUSES = (
        ('open', 'Ouvert'),
        ('in_progress', 'En cours'),
        ('resolved', 'Résolu'),
    )
    PRIORITIES = (
        (PRIORITY_DEDICATED, 'Ligne dédiée'),
        (PRIORITY_PRIORITY, 'Prioritaire'),
        (PRIORITY_STANDARD, 'Standard'),
    )

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets')
    author_role = models.CharField(max_length=20, blank=True, default='')
    store = models.ForeignKey('stores.Store', null=True, blank=True, on_delete=models.SET_NULL,
                              related_name='support_tickets')
    plan_name = models.CharField(max_length=100, blank=True, default='', help_text="Forfait du commerce à l'ouverture")
    subject = models.CharField(max_length=150)
    message = models.TextField(max_length=4000)
    category = models.CharField(max_length=20, choices=CATEGORIES, default='other')
    status = models.CharField(max_length=20, choices=STATUSES, default='open')
    priority = models.CharField(max_length=20, choices=PRIORITIES, default=PRIORITY_STANDARD)
    priority_rank = models.PositiveSmallIntegerField(default=2, editable=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # Priorité d'abord, puis la plus ancienne (celle qui attend depuis le plus longtemps).
        ordering = ['priority_rank', 'created_at']
        indexes = [models.Index(fields=['status', 'priority_rank', 'created_at'])]
        verbose_name = "Demande d'assistance"
        verbose_name_plural = "Demandes d'assistance"

    def __str__(self):
        return f"#{self.pk} {self.subject}"

    def save(self, *args, **kwargs):
        self.priority_rank = PRIORITY_RANKS.get(self.priority, 2)
        super().save(*args, **kwargs)

    @property
    def is_priority(self):
        return self.priority != PRIORITY_STANDARD


class SupportReply(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                               related_name='support_replies')
    message = models.TextField(max_length=4000)
    is_staff_reply = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = "Réponse d'assistance"
        verbose_name_plural = "Réponses d'assistance"

    def __str__(self):
        return f"Réponse #{self.pk} au ticket #{self.ticket_id}"
