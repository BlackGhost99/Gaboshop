"""Services métier pour la gestion des produits"""
import logging
from django.db import transaction, models
from django.utils import timezone
from products.models import Product
from stores.models import Store

logger = logging.getLogger(__name__)


class ProductService:
    """Services métier pour la gestion des produits"""
    
    @staticmethod
    def create_product(store, product_data):
        """
        Créer un nouveau produit avec validation métier
        """
        try:
            with transaction.atomic():
                # Vérifier que l'utilisateur peut gérer ce magasin
                if store.manager != product_data.get('request_user', None):
                    raise ValueError("Non autorisé à ajouter des produits à ce magasin.")
                
                # Validation du prix
                price = product_data.get('price', 0)
                if price <= 0:
                    raise ValueError("Le prix doit être supérieur à 0.")
                
                # Validation du stock initial
                stock = product_data.get('stock', 0)
                if stock < 0:
                    raise ValueError("Le stock ne peut pas être négatif.")
                
                # Créer le produit
                product = Product.objects.create(
                    store=store,
                    **{k: v for k, v in product_data.items() if k != 'request_user'}
                )
                
                logger.info(f"📦 Produit créé: {product.name} dans {store.name}")
                return product
                
        except Exception as e:
            logger.error(f"❌ Erreur création produit: {e}")
            raise
    
    @staticmethod
    def update_product_stock(product_id, new_stock, reason="ajustement"):
        """
        Mettre à jour le stock d'un produit avec historique
        """
        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(id=product_id)
                
                old_stock = product.stock
                product.stock = new_stock
                
                # Désactiver le produit si stock épuisé
                if new_stock == 0:
                    product.is_available = False
                
                product.save()
                
                # Log de l'ajustement de stock
                logger.info(
                    f"📊 Stock ajusté: {product.name} "
                    f"({old_stock} → {new_stock}) - Raison: {reason}"
                )
                
                return product
                
        except Product.DoesNotExist:
            logger.error(f"❌ Produit {product_id} non trouvé")
            raise ValueError("Produit non trouvé")
    
    @staticmethod
    def check_products_availability(order_items):
        """
        Vérifier la disponibilité de tous les produits d'une commande
        """
        unavailable_products = []
        
        for item_data in order_items:
            try:
                product = Product.objects.get(
                    id=item_data['product_id'],
                    is_available=True
                )
                
                if not product.check_stock(item_data['quantity']):
                    unavailable_products.append({
                        'product': product.name,
                        'requested': item_data['quantity'],
                        'available': product.stock
                    })
                    
            except Product.DoesNotExist:
                unavailable_products.append({
                    'product': f"ID {item_data['product_id']}",
                    'requested': item_data['quantity'],
                    'available': 0,
                    'error': 'Produit non trouvé'
                })
        
        return unavailable_products
    
    @staticmethod
    def get_low_stock_products(store_id, threshold=5):
        """
        Récupérer les produits avec stock faible
        """
        return Product.objects.filter(
            store_id=store_id,
            stock__lte=threshold,
            stock__gt=0,
            is_available=True
        ).order_by('stock')
    
    @staticmethod
    def get_out_of_stock_products(store_id):
        """
        Récupérer les produits en rupture de stock
        """
        return Product.objects.filter(
            store_id=store_id,
            stock=0,
            is_available=False
        )
