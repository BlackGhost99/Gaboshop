"""
Finance signals - Auto-tracking for B2B orders as expenses
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from orders.models import Order
from .models import Expense
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def auto_track_b2b_order_as_expense(sender, instance, created, **kwargs):
    """
    Auto-track B2B orders as expenses when they are delivered.
    
    When a B2C store places a B2B order (is_b2b=True and source_store is set),
    and that order is marked as delivered, automatically create an Expense entry
    for the source store (the buyer).
    """
    try:
        # Only process B2B orders
        if not instance.is_b2b or not instance.source_store:
            return
        
        # Only process when order is delivered
        if instance.status != 'delivered':
            return
        
        # Check if expense already exists for this order
        if Expense.objects.filter(b2b_order=instance).exists():
            logger.debug(f"Expense already exists for B2B order {instance.order_number}")
            return
    
        # Get or create supplier (the wholesaler/seller store)
        from .models import Supplier
        from django.utils import timezone
        
        with transaction.atomic():
            supplier, _ = Supplier.objects.get_or_create(
                store=instance.source_store,
                name=instance.store.name,  # The wholesaler
                defaults={
                    'contact_person': instance.store.manager.get_full_name() if instance.store.manager else None,
                    'phone': getattr(instance.store, 'phone', None),
                }
            )
            
            # Determine expense date (use delivered_at if available, otherwise updated_at, fallback to now)
            if instance.delivered_at:
                expense_date = instance.delivered_at.date() if hasattr(instance.delivered_at, 'date') else instance.delivered_at
            elif instance.updated_at:
                expense_date = instance.updated_at.date() if hasattr(instance.updated_at, 'date') else instance.updated_at
            else:
                expense_date = timezone.now().date()
            
            # Create expense for the buyer store
            expense = Expense.objects.create(
                store=instance.source_store,  # The buyer (B2C store)
                expense_type='APPROVISIONNEMENT',
                supplier=supplier,
                supplier_name=instance.store.name,  # Also store as text for safety
                reference=instance.order_number,
                amount=instance.total_amount,
                currency='XAF',
                expense_date=expense_date,
                payment_method='AUTRE',  # Default since Order doesn't have payment_method field
                payment_status='PAID',  # Assume paid since order was delivered
                notes=f"Commande B2B #{instance.order_number} - Auto-trackée",
                b2b_order=instance,
                created_by=instance.source_store.manager if instance.source_store.manager else None,
            )
            
            logger.info(f"✅ Dépense auto-créée pour la commande B2B {instance.order_number}: {expense.amount} FCFA")
    
    except Exception as e:
        logger.error(f"❌ Erreur lors de la création automatique de la dépense pour la commande B2B {instance.order_number}: {str(e)}", exc_info=True)
