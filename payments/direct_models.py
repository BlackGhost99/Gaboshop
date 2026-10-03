"""Auditable records for payments made directly between order participants.

These records acknowledge money received outside Gaboshop. They never initiate
a transfer and intentionally remain separate from provider Payment/Payout rows.
"""
from decimal import Decimal
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class PaymentArrangement(models.Model):
    FLOW_CHOICES = [
        ('direct_split', 'Produits au commerce, livraison au livreur'),
        ('store_collects_all', 'Tout au commerce, qui règle le livreur'),
        ('courier_cash', 'Espèces collectées par le livreur'),
        ('platform_online', 'Paiement en ligne à Gaboshop'),
    ]

    order = models.OneToOneField('orders.Order', on_delete=models.PROTECT, related_name='payment_arrangement')
    store = models.ForeignKey('stores.Store', on_delete=models.PROTECT, related_name='payment_arrangements')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    flow = models.CharField(max_length=30, choices=FLOW_CHOICES)
    method = models.CharField(max_length=30)
    delivery_method = models.CharField(max_length=30, blank=True)
    policy_snapshot = models.JSONField(default=dict)
    products_amount = models.DecimalField(max_digits=14, decimal_places=2)
    delivery_amount = models.DecimalField(max_digits=14, decimal_places=2)
    commission_amount = models.DecimalField(max_digits=14, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=7, decimal_places=4, default=Decimal('0'))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(condition=models.Q(products_amount__gte=0), name='direct_products_nonnegative'),
            models.CheckConstraint(condition=models.Q(delivery_amount__gte=0), name='direct_delivery_nonnegative'),
            models.CheckConstraint(condition=models.Q(commission_amount__gte=0), name='direct_commission_nonnegative'),
        ]


class PaymentObligation(models.Model):
    KIND_CHOICES = [
        ('products', 'Règlement du client'),
        ('delivery', 'Rémunération du livreur'),
        ('delivery_collection', 'Encaissement des frais de livraison'),
        ('courier_remittance', 'Reversement des espèces au commerce'),
        ('commission', 'Commission Gaboshop'),
        ('failed_trip', 'Indemnité course échouée'),
    ]
    STATUS_CHOICES = [
        ('not_due', 'Non exigible'), ('unpaid', 'Impayé'), ('pending', 'En attente'),
        ('partially_paid', 'Partiellement payé'), ('paid', 'Payé'), ('overdue', 'En retard'),
        ('waived', 'Exonéré'), ('cancelled', 'Annulé'),
        ('partially_refunded', 'Partiellement remboursé'), ('refunded', 'Remboursé'),
    ]
    ROLE_CHOICES = [('client', 'Client'), ('store', 'Commerce'), ('courier', 'Livreur'), ('platform', 'Gaboshop')]

    arrangement = models.ForeignKey(PaymentArrangement, on_delete=models.PROTECT, related_name='obligations')
    kind = models.CharField(max_length=30, choices=KIND_CHOICES)
    payer = models.CharField(max_length=15, choices=ROLE_CHOICES)
    payee = models.CharField(max_length=15, choices=ROLE_CHOICES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='unpaid', db_index=True)
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    requires_delivery_proof = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(fields=['arrangement', 'kind'], name='direct_unique_obligation_kind'),
            models.CheckConstraint(condition=models.Q(amount__gte=0), name='direct_obligation_nonnegative'),
        ]

    @property
    def received_amount(self):
        return sum((r.amount for r in self.receipts.filter(status='confirmed')), Decimal('0'))

    @property
    def refunded_amount(self):
        return sum((a.amount for a in self.adjustments.filter(adjustment_type__in=['refund', 'commission_credit'], status='confirmed')), Decimal('0'))

    @property
    def remaining_amount(self):
        return max(Decimal('0'), self.amount - self.received_amount - self.refunded_amount)


class CommissionSettlement(models.Model):
    STATUS_CHOICES = [('draft', 'Brouillon'), ('pending_confirmation', 'À confirmer'), ('confirmed', 'Confirmé'), ('cancelled', 'Annulé')]
    receipt_number = models.CharField(max_length=40, unique=True, editable=False)
    store = models.ForeignKey('stores.Store', on_delete=models.PROTECT, related_name='commission_settlements')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=30)
    reference = models.CharField(max_length=150, blank=True)
    comment = models.TextField(blank=True)
    proof = models.FileField(upload_to='payments/settlement_proofs/', blank=True, null=True)
    collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='collected_settlements')
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='confirmed_settlements', null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pending_confirmation')
    paid_at = models.DateTimeField(default=timezone.now)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f'REC-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)


class SettlementAllocation(models.Model):
    settlement = models.ForeignKey(CommissionSettlement, on_delete=models.PROTECT, related_name='allocations')
    obligation = models.ForeignKey(PaymentObligation, on_delete=models.PROTECT, related_name='settlement_allocations')
    amount = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['settlement', 'obligation'], name='unique_settlement_obligation'),
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='settlement_allocation_positive'),
        ]


class PaymentReceipt(models.Model):
    """Append-only evidence of a recipient's acknowledgement, not a transfer."""
    STATUS_CHOICES = [('pending', 'À confirmer'), ('confirmed', 'Confirmé'), ('rejected', 'Rejeté')]
    obligation = models.ForeignKey(PaymentObligation, on_delete=models.PROTECT, related_name='receipts')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    method = models.CharField(max_length=30)
    reference = models.CharField(max_length=150)
    receipt_number = models.CharField(max_length=40, unique=True, editable=False)
    proof = models.FileField(upload_to='payments/receipt_proofs/', blank=True, null=True)
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+', null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    idempotency_key = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='direct_receipt_positive'),
            models.UniqueConstraint(fields=['obligation', 'reference'], name='direct_unique_receipt_reference'),
        ]

    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = f'PAY-{timezone.now():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}'
        super().save(*args, **kwargs)


class PaymentAdjustment(models.Model):
    """An admin records a refund already effected by the recipient.

Commission credits are calculated from product refunds, without changing the
original order amounts or fabricating outgoing provider transactions.
"""
    TYPE_CHOICES = [('refund', 'Remboursement'), ('commission_credit', 'Avoir commission'), ('correction', 'Correction')]
    STATUS_CHOICES = [('pending', 'À confirmer'), ('confirmed', 'Confirmé'), ('cancelled', 'Annulé')]
    obligation = models.ForeignKey(PaymentObligation, on_delete=models.PROTECT, related_name='adjustments')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='+')
    adjustment_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='refund')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='confirmed')
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reason = models.TextField()
    reference = models.CharField(max_length=150)
    idempotency_key = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at', 'id']
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='direct_adjustment_positive'),
            models.UniqueConstraint(fields=['obligation', 'reference'], name='direct_unique_refund_reference'),
        ]
