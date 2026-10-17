import json
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import ProductCategory, Product
from .models import ProductVariant, ProductImage


class ProductVariantSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)

    class Meta:
        model = ProductVariant
        fields = ['id', 'name', 'sku', 'price', 'stock', 'attributes', 'created_at']
        read_only_fields = ['id', 'created_at']


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.CharField(source='image.url', read_only=True)

    class Meta:
        model = ProductImage
        fields = ['id', 'image', 'image_url', 'alt_text', 'order']
        read_only_fields = ['id', 'image_url']

class ProductCategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)
    store_category = serializers.PrimaryKeyRelatedField(read_only=True)
    commission_rate = serializers.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        required=True,
        help_text="Taux de commission en % (0-100)"
    )

    class Meta:
        model = ProductCategory
        fields = ['id', 'name', 'description', 'order', 'product_count', 'store_category', 'commission_rate']
    
    def validate_commission_rate(self, value):
        """Valide que le taux de commission est entre 0 et 100"""
        if value < 0 or value > 100:
            raise serializers.ValidationError(
                _('Le taux de commission doit être entre 0 et 100.')
            )
        return value

ALLOWED_ATTRIBUTE_KEYS = ('brand', 'model', 'sizes', 'color')


class ProductAttributesField(serializers.JSONField):
    """Caractéristiques produit (marque, modèle, tailles...). Accepte aussi une chaîne JSON (formulaire multipart)."""

    def to_internal_value(self, data):
        if isinstance(data, str):
            try:
                data = json.loads(data) if data.strip() else {}
            except ValueError:
                raise serializers.ValidationError(_('Caractéristiques invalides.'))
        if not isinstance(data, dict):
            raise serializers.ValidationError(_('Caractéristiques invalides.'))
        from products.options import join_values
        if isinstance(data.get('sizes'), list):
            data['sizes'] = ', '.join(str(v) for v in data['sizes'])
        if isinstance(data.get('color'), list):
            data['color'] = ', '.join(str(v) for v in data['color'])
        cleaned = {
            k: str(v).strip()[:300 if k in ('sizes', 'color') else 100]
            for k, v in data.items()
            if k in ALLOWED_ATTRIBUTE_KEYS and v not in (None, '') and str(v).strip()
        }
        # Tailles et couleurs rangées en liste propre « 40, 41, 42 », même tapées sans virgules.
        for key in ('sizes', 'color'):
            if key in cleaned:
                cleaned[key] = join_values(cleaned[key])
                if not cleaned[key]:
                    del cleaned[key]
        return cleaned


class ProductSerializer(serializers.ModelSerializer):
    """Serializer de base pour les produits"""
    store_name = serializers.CharField(source='store.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    has_discount = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'store', 'store_name', 
            'category', 'category_name', 'price', 'compare_price',
            'has_discount', 'discount_percentage', 'stock', 
            'sku', 'barcode', 'is_available', 'is_featured',
            'weight_kg', 'length_m', 'estimated_weight_kg', 'attributes',
            'image', 'image_2', 'image_3', 'images', 'created_at', 'sponsored'
        ]
        read_only_fields = ['store', 'created_at']

    images = ProductImageSerializer(many=True, read_only=True)
    sponsored = serializers.SerializerMethodField()

    def get_sponsored(self, obj):
        # Annoté par la liste publique ; ailleurs, pas de mention « Sponsorisé ».
        return bool(getattr(obj, 'sponsored_now', False))

class ProductDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un produit"""
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_zone = serializers.CharField(source='store.zone', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    has_discount = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'store', 'store_name', 'store_zone',
            'category', 'category_name', 'price', 'compare_price',
            'has_discount', 'discount_percentage', 'stock', 
            'sku', 'barcode', 'is_available', 'is_featured',
            'weight_kg', 'length_m', 'estimated_weight_kg', 'attributes',
            'image', 'image_2', 'image_3', 'created_at', 'updated_at',
            'variants', 'images'
        ]
        read_only_fields = ['store', 'created_at', 'updated_at']

    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

def category_allowed(category, store):
    """Catégorie de produit permise pour ce commerce.

    Sa propre catégorie ou une catégorie générale de son type : toujours. Une catégorie d'un autre type
    (une épicerie qui vend aussi des vêtements) : oui, sauf si elle sert à payer moins de commission,
    c'est-à-dire une catégorie alimentaire pour un commerce non alimentaire (0 % en Business), ou un taux
    plus bas que celui des catégories de son propre type. Une grande surface (type « vend de tout ») : toutes."""
    if category is None or store is None:
        return True
    if category.store_id:
        return category.store_id == store.id
    if category.store_category_id == store.category_id:
        return True
    if store.category_id and store.category.sells_everything:
        return True  # grande surface : chaque produit prend le taux de sa propre catégorie
    from decimal import Decimal
    from payments.subscription_check import SubscriptionChecker
    from products.models import ProductCategory
    if SubscriptionChecker._is_food_category(category) and not SubscriptionChecker._is_food_category(
            ProductCategory(store_category=store.category) if store.category_id else None):
        return False
    own = ProductCategory.objects.filter(store__isnull=True, store_category_id=store.category_id) \
        .exclude(commission_rate=None).values_list('commission_rate', flat=True)
    floor = min(own, default=None)
    if floor is None:
        floor = store.commission_rate or Decimal('0')
    return Decimal(category.commission_rate or 0) >= Decimal(floor)


def check_promotion_allowed(store):
    """Un prix barré (promotion) est un outil du forfait Pro ; une promotion déjà en place reste."""
    from payments.plan_features import required_message, store_has
    if store is not None and not store_has(store, 'promotions'):
        raise serializers.ValidationError({'compare_price': required_message('promotions', store.get_current_plan())})


def validate_positive_price(value):
    """Un produit ne se vend jamais à 0 F ou moins (faute de frappe, import mal lu)."""
    if value is not None and value <= 0:
        raise serializers.ValidationError(_('Le prix doit être plus grand que 0.'))
    return value


class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de produit"""
    attributes = ProductAttributesField(required=False)

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'category', 'price', 'compare_price',
            'stock', 'sku', 'barcode', 'is_featured', 'image',
            'image_2', 'image_3', 'weight_kg', 'length_m', 'attributes'
        ]
    
    def validate_price(self, value):
        return validate_positive_price(value)

    def validate(self, attrs):
        if not category_allowed(attrs.get('category'), self.context.get('store')):
            raise serializers.ValidationError({'category': _('Choisissez une catégorie de votre type de commerce.')})
        
        # Validation du prix
        if attrs.get('compare_price') and attrs['price'] >= attrs['compare_price']:
            raise serializers.ValidationError({
                'compare_price': _('Le prix de comparaison doit être supérieur au prix actuel.')
            })
        if attrs.get('compare_price'):
            check_promotion_allowed(self.context.get('store'))
        
        # Poids obligatoire et > 0
        weight = attrs.get('weight_kg')
        if weight is None or weight <= 0:
            raise serializers.ValidationError({
                'weight_kg': _('Le poids du produit est obligatoire et doit être supérieur à 0 (en kg).')
            })

        # Longueur obligatoire et > 0
        length = attrs.get('length_m')
        if length is None or length <= 0:
            raise serializers.ValidationError({
                'length_m': _('La longueur du produit est obligatoire et doit être supérieure à 0 (en mètres).')
            })
        if length > 5:
            raise serializers.ValidationError({
                'length_m': _('La longueur du produit ne doit pas dépasser 5 mètres.')
            })
        
        return attrs

class ProductUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour la mise à jour de produit"""
    attributes = ProductAttributesField(required=False)

    class Meta:
        model = Product
        fields = [
            'name', 'description', 'category', 'price', 'compare_price',
            'stock', 'sku', 'barcode', 'is_available', 'is_featured',
            'image', 'image_2', 'image_3', 'weight_kg', 'length_m', 'attributes'
        ]

    def validate_price(self, value):
        return validate_positive_price(value)

    def validate(self, attrs):
        compare = attrs.get('compare_price')
        if compare and self.instance is not None and compare != self.instance.compare_price:
            price = attrs.get('price', self.instance.price)
            if price is not None and price >= compare:
                raise serializers.ValidationError({
                    'compare_price': _('Le prix avant promo doit être supérieur au prix de vente.')
                })
            check_promotion_allowed(self.instance.store)
        return attrs

    def validate_category(self, value):
        if self.instance is not None and not category_allowed(value, self.instance.store):
            raise serializers.ValidationError(_('Choisissez une catégorie de votre type de commerce.'))
        return value

    def validate_is_available(self, value):
        if value and self.instance is not None and self.instance.blocked_by_admin:
            raise serializers.ValidationError(_('Ce produit a été retiré par Gaboshop : seul l’administrateur peut le remettre en vente.'))
        return value

    def validate_length_m(self, value):
        if value is None:
            return value
        if value <= 0:
            raise serializers.ValidationError(_('La longueur doit être supérieure à 0 (en mètres).'))
        if value > 5:
            raise serializers.ValidationError(_('La longueur ne doit pas dépasser 5 mètres.'))
        return value


# ProductCategoryTemplate serializer removed after merging templates into ProductCategory
