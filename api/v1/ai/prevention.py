"""
Service de prévention des erreurs et ruptures
"""
from typing import Dict, Any, Optional, List
from decimal import Decimal
from products.models import Product
from orders.models import Order, OrderItem
from stores.models import Store


class PreventionService:
    """
    Service pour prévenir les erreurs avant qu'elles ne se produisent
    """
    
    @staticmethod
    def check_stock_before_payment(order: Order) -> tuple[bool, Optional[str], List[Dict]]:
        """
        Vérifie le stock avant le paiement
        
        Returns:
            (can_proceed, warning_message, alternatives)
        """
        order_items = OrderItem.objects.filter(order=order)
        warnings = []
        alternatives = []
        
        for item in order_items:
            product = item.product
            requested_qty = item.quantity
            
            if product.stock < requested_qty:
                # Stock insuffisant
                warning = f"Stock insuffisant pour '{product.name}'. Disponible: {product.stock}, Demandé: {requested_qty}"
                warnings.append({
                    "product_id": product.id,
                    "product_name": product.name,
                    "available": product.stock,
                    "requested": requested_qty,
                    "message": warning,
                })
                
                # Chercher des alternatives (même catégorie, même magasin)
                alternatives_products = Product.objects.filter(
                    store=product.store,
                    category=product.category,
                    is_available=True,
                    stock__gte=requested_qty
                ).exclude(id=product.id)[:3]
                
                for alt in alternatives_products:
                    alternatives.append({
                        "product_id": alt.id,
                        "product_name": alt.name,
                        "price": float(alt.price),
                        "stock": alt.stock,
                    })
        
        if warnings:
            message = f"⚠️ {len(warnings)} produit(s) avec stock insuffisant. Vérifiez avant de payer."
            return False, message, alternatives
        
        return True, None, []
    
    @staticmethod
    def suggest_alternatives(product_id: int, quantity: int = 1) -> List[Dict]:
        """
        Suggère des alternatives à un produit
        """
        try:
            product = Product.objects.get(id=product_id)
        except Product.DoesNotExist:
            return []
        
        # Chercher dans la même catégorie et magasin
        alternatives = Product.objects.filter(
            store=product.store,
            category=product.category,
            is_available=True,
            stock__gte=quantity
        ).exclude(id=product_id).order_by('price')[:5]
        
        return [
            {
                "product_id": alt.id,
                "product_name": alt.name,
                "price": float(alt.price),
                "stock": alt.stock,
                "similarity": "même catégorie",
            }
            for alt in alternatives
        ]
    
    @staticmethod
    def block_checkout_if_risk(order: Order, risk_threshold: float = 0.5) -> tuple[bool, Optional[str]]:
        """
        Bloque le checkout si le risque est trop élevé
        
        risk_threshold: 0.0 à 1.0 (0.5 = 50% de risque)
        """
        # Calculer le risque
        risk_factors = []
        
        # Facteur 1: Stock insuffisant
        can_proceed, stock_warning, _ = PreventionService.check_stock_before_payment(order)
        if not can_proceed:
            risk_factors.append(0.8)  # Risque élevé
        
        # Facteur 2: Magasin fermé
        if not order.store.is_open():
            risk_factors.append(0.9)
        
        # Facteur 3: Montant minimum non atteint
        if order.store.min_order_amount and order.items_total < order.store.min_order_amount:
            risk_factors.append(0.3)
        
        # Calculer le risque total
        if not risk_factors:
            return True, None
        
        total_risk = sum(risk_factors) / len(risk_factors) if risk_factors else 0
        
        if total_risk >= risk_threshold:
            reasons = []
            if not can_proceed:
                reasons.append("stock insuffisant")
            if not order.store.is_open():
                reasons.append("magasin fermé")
            
            message = f"⚠️ Checkout bloqué: {', '.join(reasons)}. Risque: {int(total_risk * 100)}%"
            return False, message
        
        return True, None

