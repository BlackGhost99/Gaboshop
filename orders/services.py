"""Services métier pour la gestion des commandes"""
import logging
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from orders.models import Order, OrderItem
from products.models import Product
# Persisted notifications service (DB + multi-canal)
from notifications.service import NotificationService
from products.services import ProductService

logger = logging.getLogger(__name__)


class OrderService:
    """Services métier pour la gestion des commandes"""
    
    @staticmethod
    def create_order(client, store, order_data):
        """
        Créer une nouvelle commande avec validation complète
        """
        try:
            with transaction.atomic():
                # Vérifications préalables
                if not store.is_active:
                    raise ValueError("Le magasin n'est pas actif.")
                
                if not store.is_open():
                    raise ValueError("Le magasin est fermé.")
                
                items_data = order_data.get('items', [])
                if not items_data:
                    raise ValueError("La commande doit contenir des articles.")
                
                # Vérifier la disponibilité des produits
                unavailable_products = ProductService.check_products_availability(items_data)
                if unavailable_products:
                    raise ValueError(f"Produits non disponibles: {unavailable_products}")
                
                # Calculer les totaux
                items_total = sum(
                    item['unit_price'] * item['quantity'] 
                    for item in items_data
                )
                
                # Vérifier le montant minimum
                if items_total < store.min_order_amount:
                    raise ValueError(
                        f"Montant minimum non atteint: {items_total} < {store.min_order_amount}"
                    )
                
                # Créer la commande
                order = Order.objects.create(
                    client=client,
                    store=store,
                    delivery_address=order_data.get('delivery_address'),
                    delivery_phone=order_data.get('delivery_phone'),
                    delivery_zone=order_data.get('delivery_zone'),
                    notes=order_data.get('notes', ''),
                    items_total=items_total,
                    delivery_fee=store.delivery_fee,
                    tax_amount=Decimal('0.00'),  # TVA? À configurer
                    total_amount=items_total + store.delivery_fee
                )
                
                # Créer les OrderItems et mettre à jour les stocks
                for item_data in items_data:
                    product = Product.objects.get(id=item_data['product_id'])
                    
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        quantity=item_data['quantity'],
                        unit_price=item_data['unit_price']
                    )
                    
                    # Réduire le stock
                    product.reduce_stock(item_data['quantity'])
                
                logger.info(f"🛒 Commande créée: #{order.order_number} - {order.total_amount} FCFA")
                
                # Notifier le magasin
                NotificationService.notify_new_order(order)
                
                return order
                
        except Exception as e:
            logger.error(f"❌ Erreur création commande: {e}")
            raise
    
    @staticmethod
    def update_order_status(order, new_status, user):
        """
        Mettre à jour le statut d'une commande avec validation
        """
        try:
            old_status = order.status
            
            # Validation des transitions selon le type d'utilisateur
            valid_transitions = OrderService._get_valid_transitions(user, old_status)
            
            if new_status not in valid_transitions:
                raise ValueError(
                    f"Transition non autorisée: {old_status} → {new_status}"
                )
            
            # Mettre à jour le statut
            order.status = new_status
            
            # Mettre à jour les timestamps
            if new_status == 'confirmed' and not order.confirmed_at:
                order.confirmed_at = timezone.now()
            elif new_status == 'delivered' and not order.delivered_at:
                order.delivered_at = timezone.now()
            
            order.save()
            
            # Notifier le client du changement
            NotificationService.notify_order_status_update(order, old_status, new_status)
            
            logger.info(
                f"📦 Statut commande #{order.order_number} mis à jour: "
                f"{old_status} → {new_status} par {user.phone}"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"❌ Erreur mise à jour statut: {e}")
            raise
    
    @staticmethod
    def _get_valid_transitions(user, current_status):
        """
        Déterminer les transitions valides selon le type d'utilisateur
        """
        base_transitions = {
            'pending': ['cancelled'],
            'confirmed': ['preparing', 'cancelled'],
            'preparing': ['ready', 'cancelled'],
            'ready': ['assigned', 'cancelled'],
            'assigned': ['in_transit', 'cancelled'],
            'in_transit': ['delivered', 'cancelled'],
            'delivered': [],
            'cancelled': [],
            'refunded': [],
        }
        
        # Ajouter des transitions spécifiques selon le rôle
        if user.is_store_manager():
            if current_status == 'pending':
                base_transitions['pending'].append('confirmed')
        
        elif user.is_delivery_agent():
            if current_status == 'assigned':
                base_transitions['assigned'].append('in_transit')
            elif current_status == 'in_transit':
                base_transitions['in_transit'].append('delivered')
        
        return base_transitions.get(current_status, [])
    
    @staticmethod
    def calculate_order_commission(order):
        """
        Calculer la commission GABOSHOP sur une commande
        """
        try:
            from payments.models import CategoryCommission

            total_commission = Decimal('0.00')
            # Determine plan multiplier
            plan = order.store.get_current_plan()
            multiplier = Decimal(getattr(plan, 'commission_multiplier', 1)) if plan else Decimal('1')

            # Sum commission per item using category base rates
            for item in order.items.all():
                product = item.product
                item_subtotal = item.subtotal
                base_rate = None
                if product and product.category and product.category.store_category:
                    try:
                        cc = CategoryCommission.objects.get(store_category=product.category.store_category)
                        base_rate = Decimal(cc.base_rate)
                    except CategoryCommission.DoesNotExist:
                        base_rate = None

                if base_rate is None:
                    base_rate = Decimal(order.store.commission_rate or Decimal('0.00'))

                effective_rate = (base_rate * Decimal(multiplier))
                item_comm = (item_subtotal * effective_rate) / Decimal('100')
                total_commission += item_comm

            # Platform share of delivery fee (40%)
            delivery_fee_share = (order.delivery_fee * Decimal('0.4'))

            # Effective commission rate as percentage for display/storage
            commission_rate_pct = (total_commission / order.items_total * Decimal('100')) if order.items_total > 0 else Decimal('0.00')

            return {
                'commission_rate': commission_rate_pct.quantize(Decimal('0.01')),
                'commission_amount': total_commission.quantize(Decimal('0.01')),
                'delivery_fee_share': delivery_fee_share.quantize(Decimal('0.01')),
                'store_earnings': (order.items_total - total_commission).quantize(Decimal('0.01')),
                'agent_earnings': delivery_fee_share.quantize(Decimal('0.01'))
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul commission: {e}")
            return None
    
    @staticmethod
    def cancel_order(order, reason="Client"):
        """
        Annuler une commande et restaurer les stocks
        """
        try:
            with transaction.atomic():
                # Vérifier que la commande peut être annulée
                if order.status in ['delivered', 'refunded']:
                    raise ValueError("Impossible d'annuler cette commande.")
                
                # Restaurer les stocks
                for item in order.items.all():
                    product = item.product
                    product.stock += item.quantity
                    product.is_available = True
                    product.save()
                
                # Marquer comme annulée
                order.status = 'cancelled'
                order.save()
                
                logger.info(
                    f"❌ Commande #{order.order_number} annulée - Raison: {reason}"
                )
                
                return order
                
        except Exception as e:
            logger.error(f"❌ Erreur annulation commande: {e}")
            raise
