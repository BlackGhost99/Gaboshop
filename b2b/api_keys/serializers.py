from rest_framework import serializers

from b2b.models import WholesalerApiKey
from orders.models import Order
from products.models import Product
from products.serializers import validate_positive_price

MAX_STOCK = 2147483647


class ApiKeySerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()

    class Meta:
        model = WholesalerApiKey
        fields = ['id', 'name', 'prefix', 'created_at', 'last_used_at', 'revoked_at', 'is_active', 'status']
        read_only_fields = fields

    def get_status(self, obj):
        return 'active' if obj.is_active else 'revoked'


class ApiKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=80, trim_whitespace=True,
        error_messages={
            'required': 'Donnez un nom à cette clé (ex. « Logiciel de caisse »).',
            'blank': 'Donnez un nom à cette clé (ex. « Logiciel de caisse »).',
            'max_length': 'Le nom ne peut pas dépasser 80 caractères.',
        })


class IntegrationProductSerializer(serializers.ModelSerializer):
    b2b_prices = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'sku', 'barcode', 'price', 'stock', 'is_available', 'b2b_prices', 'updated_at']
        read_only_fields = fields

    def get_b2b_prices(self, obj):
        """Prix par palier de quantité fixés avec Gaboshop : en lecture seule."""
        return [{'min_quantity': p.min_quantity, 'max_quantity': p.max_quantity, 'price': str(p.b2b_price)}
                for p in obj.b2b_pricings.all() if p.is_active and p.b2b_store_id == obj.store_id]


class IntegrationProductUpdateSerializer(serializers.Serializer):
    """Seuls le stock et le prix se modifient, avec les règles de l'application (stock >= 0, prix > 0)."""
    stock = serializers.IntegerField(
        required=False, min_value=0, max_value=MAX_STOCK,
        error_messages={
            'invalid': 'Le stock doit être un nombre entier.',
            'min_value': 'Le stock ne peut pas être négatif.',
            'max_value': 'Ce stock est trop grand.',
        })
    price = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=2,
        error_messages={
            'invalid': 'Le prix doit être un nombre (ex. 4500 ou 4500.50).',
            'max_digits': 'Ce prix est trop grand.',
            'max_decimal_places': 'Le prix a au plus 2 décimales.',
            'max_whole_digits': 'Ce prix est trop grand.',
        })

    def validate_price(self, value):
        return validate_positive_price(value)

    def validate(self, attrs):
        extra = sorted(set(self.initial_data) - set(self.fields))
        if extra:
            raise serializers.ValidationError(
                f"Seuls « stock » et « price » se modifient par l'API (reçu : {', '.join(extra)}).")
        if not attrs:
            raise serializers.ValidationError('Indiquez au moins un champ à modifier : « stock » ou « price ».')
        return attrs


class IntegrationOrderSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    buyer_store = serializers.CharField(source='source_store.name', default='', read_only=True)
    items_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'order_number', 'status', 'status_display', 'buyer_store', 'items_total', 'delivery_fee',
                  'total_amount', 'items_count', 'city', 'created_at', 'confirmed_at', 'delivered_at']
        read_only_fields = fields

    def get_items_count(self, obj):
        return sum(item.quantity for item in obj.items.all())


class IntegrationOrderDetailSerializer(IntegrationOrderSerializer):
    items = serializers.SerializerMethodField()

    class Meta(IntegrationOrderSerializer.Meta):
        fields = IntegrationOrderSerializer.Meta.fields + [
            'delivery_type', 'delivery_address', 'delivery_zone', 'delivery_phone', 'notes', 'items', 'updated_at']
        read_only_fields = fields

    def get_items(self, obj):
        return [{
            'id': item.id, 'product_id': item.product_id, 'product_name': item.product.name, 'sku': item.product.sku,
            'quantity': item.quantity, 'unit_price': str(item.unit_price), 'subtotal': str(item.subtotal),
        } for item in obj.items.all()]
