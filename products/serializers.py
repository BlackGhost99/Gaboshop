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
            'weight_kg', 'estimated_weight_kg',
            'image', 'image_2', 'image_3', 'created_at'
        ]
        read_only_fields = ['store', 'created_at']

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
            'weight_kg', 'estimated_weight_kg',
            'image', 'image_2', 'image_3', 'created_at', 'updated_at',
            'variants', 'images'
        ]
        read_only_fields = ['store', 'created_at', 'updated_at']

    variants = ProductVariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

class ProductCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de produit"""
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'category', 'price', 'compare_price',
            'stock', 'sku', 'barcode', 'is_featured', 'image',
            'image_2', 'image_3', 'weight_kg'
        ]
    
    def validate(self, attrs):
        request = self.context.get('request')
        
        if request and hasattr(request, 'user'):
            # Dans le contexte d'une vue, le store sera défini par la vue
            pass
        
        # Validation du prix
        if attrs.get('compare_price') and attrs['price'] >= attrs['compare_price']:
            raise serializers.ValidationError({
                'compare_price': _('Le prix de comparaison doit être supérieur au prix actuel.')
            })
        
        # Poids obligatoire et > 0
        weight = attrs.get('weight_kg')
        if weight is None or weight <= 0:
            raise serializers.ValidationError({
                'weight_kg': _('Le poids du produit est obligatoire et doit être supérieur à 0 (en kg).')
            })
        
        return attrs

class ProductUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour la mise à jour de produit"""
    class Meta:
        model = Product
        fields = [
            'name', 'description', 'category', 'price', 'compare_price',
            'stock', 'sku', 'barcode', 'is_available', 'is_featured',
            'image', 'image_2', 'image_3', 'weight_kg'
        ]


# ProductCategoryTemplate serializer removed after merging templates into ProductCategory

