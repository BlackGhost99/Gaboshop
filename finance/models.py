from django.db import models
from django.utils import timezone


class Supplier(models.Model):
    """Fournisseurs réutilisables pour les dépenses"""
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [['store', 'name']]
        ordering = ['name']
        verbose_name = "Fournisseur"
        verbose_name_plural = "Fournisseurs"
    
    def __str__(self):
        return f"{self.name} ({self.store.name})"


EXPENSE_TYPE_CHOICES = (
    ('APPROVISIONNEMENT', 'Approvisionnement'),
    ('LOGISTIQUE', 'Logistique & Transport'),
    ('PERSONNEL', 'Personnel'),
    ('LOYER', 'Loyer & Charges'),
    ('MARKETING', 'Marketing & Publicité'),
    ('AUTRE', 'Autre'),
)

PAYMENT_METHOD_CHOICES = (
    ('CASH', 'Espèces'),
    ('MOMO', 'Mobile Money'),
    ('BANK_TRANSFER', 'Virement'),
    ('CHECK', 'Chèque'),
    ('CARD', 'Carte'),
    ('AUTRE', 'Autre'),
)

PAYMENT_STATUS_CHOICES = (
    ('PAID', 'Payé'),
    ('PENDING', 'En attente'),
    ('PARTIAL', 'Partiel'),
)


class Expense(models.Model):
    """Dépenses du store (saisie manuelle ou auto-tracking B2B)"""
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='expenses')
    expense_type = models.CharField(max_length=30, choices=EXPENSE_TYPE_CHOICES)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='expenses')
    supplier_name = models.CharField(max_length=255, blank=True, help_text="Utilisé si supplier=null")
    reference = models.CharField(max_length=100, blank=True, help_text="Facture, bon de commande, etc.")
    
    # Lien optionnel vers commande B2B sortante
    b2b_order = models.OneToOneField('orders.Order', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='expense_record')
    
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='XAF')
    expense_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, default='PAID', choices=PAYMENT_STATUS_CHOICES)
    
    notes = models.TextField(blank=True)
    attachment = models.FileField(upload_to='expenses/%Y/%m/', blank=True, null=True)
    
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='expenses_created')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['store', 'expense_date']),
            models.Index(fields=['store', 'expense_type']),
        ]
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"
    
    def __str__(self):
        supplier = self.supplier.name if self.supplier else self.supplier_name or "Sans fournisseur"
        return f"{self.expense_type} - {supplier} ({self.amount} {self.currency}) - {self.expense_date}"
    
    def get_supplier_display(self):
        """Retourne le nom du fournisseur (supplier ou supplier_name)"""
        if self.supplier:
            return self.supplier.name
        return self.supplier_name or "Non spécifié"
