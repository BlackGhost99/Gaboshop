from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import StoreCategory, Store

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
    
    class Meta:
        model = Store
        fields = [
            'id', 'name', 'category', 'category_name', 'city', 'zone', 
            'phone', 'logo', 'is_active', 'is_open', 'total_products',
            'delivery_fee', 'min_order_amount', 'commission_rate'
        ]

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
            'commission_rate', 'delivery_fee', 'min_order_amount',
            'is_active', 'is_verified', 'is_open', 'total_products',
            'opening_time', 'closing_time', 'created_at'
        ]
        read_only_fields = ['created_at', 'is_verified']
    
    def get_manager_name(self, obj):
        if obj.manager.first_name and obj.manager.last_name:
            return f"{obj.manager.first_name} {obj.manager.last_name}"
        return obj.manager.phone

    def get_manager_details(self, obj):
        return {
            'first_name': obj.manager.first_name,
            'last_name': obj.manager.last_name,
            'email': obj.manager.email,
            'phone': obj.manager.phone
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
    
    def validate(self, attrs):
        user = self.context['request'].user
        
        # Vérifier que l'utilisateur est un store_manager
        if not getattr(user, 'is_store_manager', lambda: False)():
            raise serializers.ValidationError({
                'user': _('Seuls les gérants de magasin peuvent créer des magasins.')
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
            'opening_time', 'closing_time', 'delivery_fee', 'min_order_amount'
        ]
