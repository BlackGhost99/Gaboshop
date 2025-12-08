from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from .models import Delivery, DeliveryTracking, DeliveryProfile
from users.models import User

class DeliveryTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryTracking
        fields = ['id', 'status', 'location', 'latitude', 'longitude', 'notes', 'created_at']
        read_only_fields = ['id', 'created_at']

class DeliverySerializer(serializers.ModelSerializer):
    """Serializer pour les livraisons"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    client_phone = serializers.CharField(source='order.client.phone', read_only=True)
    store_name = serializers.CharField(source='order.store.name', read_only=True)
    store_address = serializers.CharField(source='pickup_address', read_only=True)
    delivery_agent_phone = serializers.CharField(source='delivery_agent.phone', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    tracking_history = DeliveryTrackingSerializer(many=True, read_only=True)
    
    class Meta:
        model = Delivery
        fields = [
            'id', 'tracking_number', 'order', 'order_number',
            'delivery_agent', 'delivery_agent_phone', 'status', 'status_display',
            'city', 'pickup_address', 'delivery_address', 'store_name', 'store_address',
            'client_phone', 'delivery_fee', 'agent_commission',
            'assigned_at', 'picked_up_at', 'delivered_at',
            'delivery_notes', 'customer_feedback', 'rating',
            'tracking_history', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'tracking_number', 'created_at', 'updated_at',
            'assigned_at', 'picked_up_at', 'delivered_at'
        ]

class DeliveryAssignSerializer(serializers.ModelSerializer):
    """Serializer pour assigner un livreur"""
    class Meta:
        model = Delivery
        fields = ['delivery_agent']
    
    def validate(self, attrs):
        delivery_agent = attrs['delivery_agent']
        
        # Vérifier que c'est bien un livreur
        if not delivery_agent.is_delivery_agent():
            raise serializers.ValidationError({
                'delivery_agent': _('L\'utilisateur doit être un livreur.')
            })
        
        # Vérifier la disponibilité
        if not delivery_agent.is_available:
            raise serializers.ValidationError({
                'delivery_agent': _('Ce livreur n\'est pas disponible.')
            })
        
        return attrs

class DeliveryStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour mettre à jour le statut de livraison"""
    location = serializers.CharField(write_only=True, required=False)
    latitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    longitude = serializers.DecimalField(max_digits=9, decimal_places=6, required=False)
    notes = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Delivery
        fields = ['status', 'location', 'latitude', 'longitude', 'notes']
    
    def update(self, instance, validated_data):
        # Extraire les données de tracking
        tracking_data = {
            'location': validated_data.pop('location', ''),
            'latitude': validated_data.pop('latitude', None),
            'longitude': validated_data.pop('longitude', None),
            'notes': validated_data.pop('notes', ''),
        }
        
        # Créer un enregistrement de tracking
        if any(tracking_data.values()):
            DeliveryTracking.objects.create(
                delivery=instance,
                status=validated_data.get('status', instance.status),
                **tracking_data
            )
        
        # Mettre à jour les timestamps selon le statut
        new_status = validated_data.get('status')
        
        if new_status == 'assigned' and not instance.assigned_at:
            instance.assigned_at = timezone.now()
        elif new_status == 'picked_up' and not instance.picked_up_at:
            instance.picked_up_at = timezone.now()
        elif new_status == 'delivered' and not instance.delivered_at:
            instance.delivered_at = timezone.now()
        
        return super().update(instance, validated_data)

class DeliveryConfirmSerializer(serializers.Serializer):
    """Serializer pour confirmer une livraison"""
    delivery_notes = serializers.CharField(required=False, allow_blank=True)
    customer_feedback = serializers.CharField(required=False, allow_blank=True)
    rating = serializers.IntegerField(min_value=1, max_value=5, required=False)
    
    def update(self, instance, validated_data):
        instance.status = 'delivered'
        instance.delivery_notes = validated_data.get('delivery_notes', '')
        instance.customer_feedback = validated_data.get('customer_feedback', '')
        instance.rating = validated_data.get('rating')
        instance.delivered_at = timezone.now()
        instance.save()
        
        return instance

class DeliveryProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryProfile
        fields = ['cin_number', 'vehicle_type', 'vehicle_plate', 'status', 'average_rating', 'total_deliveries', 'success_rate']

class DeliveryAgentSerializer(serializers.ModelSerializer):
    delivery_profile = DeliveryProfileSerializer(write_only=True, required=False)
    profile = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    daily_deliveries = serializers.SerializerMethodField()
    password = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['id', 'phone', 'email', 'first_name', 'last_name', 'name', 'city', 'profile_picture', 'is_active', 'profile', 'delivery_profile', 'daily_deliveries', 'password']
        
    def get_profile(self, obj):
        if hasattr(obj, 'delivery_profile'):
            return DeliveryProfileSerializer(obj.delivery_profile).data
        return None

    def get_name(self, obj):
        return obj.get_full_name()

    def get_daily_deliveries(self, obj):
        today = timezone.now().date()
        return Delivery.objects.filter(
            delivery_agent=obj,
            delivered_at__date=today,
            status='delivered'
        ).count()

    def create(self, validated_data):
        profile_data = validated_data.pop('delivery_profile', {})
        password = validated_data.pop('password', '123456') # Default password
        
        # Force user_type
        validated_data['user_type'] = 'delivery_agent'
        
        user = User.objects.create_user(password=password, **validated_data)
        
        # Create profile
        DeliveryProfile.objects.create(user=user, **profile_data)
        
        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('delivery_profile', {})
        
        # Update User fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update or Create Profile
        if profile_data:
            DeliveryProfile.objects.update_or_create(user=instance, defaults=profile_data)
            
        return instance
