import re
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import StoreCategory, Store

# Frais de livraison du commerce : jamais négatifs, plafonnés (FCFA).
DELIVERY_FEE_LIMITS = {
    'delivery_fee': {'min_value': 0, 'max_value': 100000},
}

class StoreCategorySerializer(serializers.ModelSerializer):
    store_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = StoreCategory
        fields = ['id', 'name', 'description', 'icon', 'is_active', 'store_count']

class StoreListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des magasins (données réduites)"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    is_open = serializers.BooleanField(read_only=True)
    total_products = serializers.IntegerField(read_only=True)
    sponsored = serializers.SerializerMethodField()
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'category', 'category_name', 'city', 'zone', 
            'phone', 'logo', 'is_active', 'is_open', 'total_products',
            'offers_delivery', 'delivery_fee', 'min_order_amount', 'commission_rate',
            'subscription_plan', 'sponsored'
        ]

    def get_sponsored(self, obj):
        # Annoté par la liste publique ; ailleurs, pas de mention « Sponsorisé ».
        return bool(getattr(obj, 'sponsored_now', False))

class StoreDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour un magasin spécifique"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    manager_name = serializers.SerializerMethodField()
    manager_details = serializers.SerializerMethodField()
    is_open = serializers.BooleanField(read_only=True)
    total_products = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'description', 'category', 'category_name',
            'manager', 'manager_name', 'manager_details', 'phone', 'email', 'address', 'city', 'zone',
            'latitude', 'longitude', 'logo', 'banner_image',
            'commission_rate', 'offers_delivery', 'delivery_fee', 'min_order_amount',
            'is_active', 'is_verified', 'is_open', 'total_products',
            'opening_time', 'closing_time', 'created_at'
        ]
        read_only_fields = ['created_at', 'is_verified']
        extra_kwargs = DELIVERY_FEE_LIMITS
    
    def _can_see_manager_contact(self, obj):
        # Le téléphone du magasin reste public ; les coordonnées personnelles du gérant, non.
        user = getattr(self.context.get('request'), 'user', None)
        if not user or not user.is_authenticated:
            return False
        return user.id == obj.manager_id or user.is_superuser or getattr(user, 'user_type', '') == 'admin'

    def get_manager_name(self, obj):
        if obj.manager.first_name and obj.manager.last_name:
            return f"{obj.manager.first_name} {obj.manager.last_name}"
        return obj.manager.phone if self._can_see_manager_contact(obj) else ''

    def get_manager_details(self, obj):
        private = self._can_see_manager_contact(obj)
        return {
            'first_name': obj.manager.first_name,
            'last_name': obj.manager.last_name,
            'email': obj.manager.email if private else '',
            'phone': obj.manager.phone if private else '',
        }

class StoreCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de magasin"""
    class Meta:
        model = Store
        fields = [
            'name', 'description', 'category', 'phone', 'email', 
            'address', 'zone', 'latitude', 'longitude', 'logo',
            'opening_time', 'closing_time', 'delivery_fee', 'min_order_amount'
        ]
        extra_kwargs = DELIVERY_FEE_LIMITS
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        # Vérifier que l'utilisateur est un store_manager
        if not getattr(user, 'is_store_manager', lambda: False)():
            raise serializers.ValidationError({
                'user': _('Seuls les commerçants peuvent créer des magasins.')
            })
        
        # Assigner automatiquement le manager
        attrs['manager'] = user
        
        return attrs

class StoreUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour la mise à jour de magasin"""
    class Meta:
        model = Store
        fields = [
            'name', 'description', 'phone', 'email', 'address', 
            'zone', 'latitude', 'longitude', 'logo', 'banner_image',
            'opening_time', 'closing_time', 'offers_delivery', 'delivery_fee', 'min_order_amount',
            'agent_code', 'payout_phone', 'stock_alert_threshold'
        ]
        extra_kwargs = {**DELIVERY_FEE_LIMITS, 'stock_alert_threshold': {'max_value': 1000}}

    def validate_agent_code(self, value):
        value = (value or '').strip()
        if value and not re.fullmatch(r'[A-Za-z0-9_.\-]{3,100}', value):
            raise serializers.ValidationError(_('Code agent invalide (lettres, chiffres, - _ . uniquement).'))
        return value

    def validate_payout_phone(self, value):
        digits = re.sub(r'\D', '', value or '')
        if not digits:
            return ''
        if len(digits) == 11 and digits.startswith('241'):
            digits = digits[3:]
        if len(digits) == 8:
            digits = '0' + digits
        if not re.fullmatch(r'0[67]\d{7}', digits):
            raise serializers.ValidationError(
                _('Numéro Mobile Money invalide : un numéro Airtel (074, 076, 077) ou Moov (060, 062, 065, 066).')
            )
        return '+241' + digits[1:]
        
