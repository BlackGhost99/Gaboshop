from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import (
    Payment,
    Commission,
    Reversement,
    PaymentIntent,
    PaymentTransaction,
    SubscriptionPlan,
    Forfait,
    ClientForfait,
    Payout,
    PaymentCallbackLog,
)

class PaymentSerializer(serializers.ModelSerializer):
    """Serializer pour les paiements"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    client_phone = serializers.CharField(source='order.client.phone', read_only=True)
    store_name = serializers.CharField(source='order.store.name', read_only=True)
    amount_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'order', 'order_number', 'client_phone', 'store_name',
            'payment_method', 'payment_method_display', 'status', 'status_display',
            'amount', 'amount_display', 'transaction_id', 'operator_reference',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'completed_at'
        ]
    
    def get_amount_display(self, obj):
        return f"{obj.amount} FCFA"

class PaymentInitSerializer(serializers.Serializer):
    """Serializer pour initialiser un paiement client."""

    # Supporte les méthodes du modèle + l'alias "mobile_money" (Airtel/Moov)
    payment_method = serializers.ChoiceField(
        choices=[choice[0] for choice in Payment.PAYMENT_METHOD_CHOICES] + ['mobile_money']
    )
    phone_number = serializers.CharField(required=False)  # Pour Airtel/Moov
    operator = serializers.ChoiceField(
        choices=[('airtel', 'Airtel Money'), ('moov', 'Moov Money')],
        required=False
    )

    def validate(self, attrs):
        method = attrs['payment_method']
        operator = attrs.get('operator')

        # Mobile money = numéro requis
        if method in ['airtel_money', 'moov_money', 'mobile_money']:
            if not attrs.get('phone_number'):
                raise serializers.ValidationError({
                    'phone_number': _('Le numéro de téléphone est requis pour Mobile Money.')
                })

            # Normaliser l'opérateur et la méthode
            if method == 'mobile_money':
                if not operator:
                    raise serializers.ValidationError({
                        'operator': _('L\'opérateur est requis pour Mobile Money.')
                    })
                if operator not in ['airtel', 'moov']:
                    raise serializers.ValidationError({
                        'operator': _('Opérateur Mobile Money invalide.')
                    })
                attrs['payment_method'] = 'airtel_money' if operator == 'airtel' else 'moov_money'
            else:
                # Déduire l'opérateur depuis la méthode si non fourni
                attrs['operator'] = 'airtel' if method == 'airtel_money' else 'moov'

            # Format standard +241
            phone = attrs['phone_number']
            if phone.startswith('0'):
                attrs['phone_number'] = '+241' + phone[1:]

        return attrs

class CommissionSerializer(serializers.ModelSerializer):
    """Serializer pour les commissions"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    order_amount_display = serializers.SerializerMethodField()
    commission_amount_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Commission
        fields = [
            'id', 'order', 'order_number', 'store', 'store_name',
            'order_amount', 'order_amount_display', 'commission_rate',
            'commission_amount', 'commission_amount_display', 'delivery_fee_share',
            'is_settled', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_order_amount_display(self, obj):
        return f"{obj.order_amount} FCFA"
    
    def get_commission_amount_display(self, obj):
        return f"{obj.commission_amount} FCFA"

class ReversementSerializer(serializers.ModelSerializer):
    """Serializer pour les reversements"""
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_phone = serializers.CharField(source='store.phone', read_only=True)
    total_sales_display = serializers.SerializerMethodField()
    total_commissions_display = serializers.SerializerMethodField()
    net_amount_display = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Reversement
        fields = [
            'id', 'store', 'store_name', 'store_phone',
            'period_start', 'period_end', 'total_orders',
            'total_sales', 'total_sales_display', 'total_commissions', 'total_commissions_display',
            'net_amount', 'net_amount_display', 'status', 'status_display',
            'transaction_reference', 'created_at', 'processed_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'processed_at', 'completed_at'
        ]
    
    def get_total_sales_display(self, obj):
        return f"{obj.total_sales} FCFA"
    
    def get_total_commissions_display(self, obj):
        return f"{obj.total_commissions} FCFA"
    
    def get_net_amount_display(self, obj):
        return f"{obj.net_amount} FCFA"


# ============================================================================
# SERIALIZERS POUR CINETPAY / AIRTEL / MOOV INTEGRATION
# ============================================================================

class CreatePaymentSerializer(serializers.Serializer):
    """Serializer pour créer un PaymentIntent"""
    order_id = serializers.IntegerField()
    provider = serializers.CharField(default="cinetpay")
    channels = serializers.CharField(required=False, default="ALL")
    lang = serializers.CharField(required=False, default="FR")
    metadata = serializers.DictField(required=False)


class PaymentIntentSerializer(serializers.ModelSerializer):
    """Serializer pour PaymentIntent"""
    class Meta:
        model = PaymentIntent
        fields = "__all__"
        read_only_fields = (
            "reference", "status", "payment_token", "payment_url", 
            "raw_response", "created_at"
        )


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer pour exposer les plans d'abonnement."""
    features = serializers.SerializerMethodField()

    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'slug', 'plan_type', 'price', 'max_products',
            'can_sponsor_products', 'has_statistics', 'has_custom_page',
            'has_priority_support', 'priority_listing', 'commission_rate',
            'commission_multiplier',
            'description', 'features_json', 'is_active', 'features'
        ]
        read_only_fields = fields

    def get_features(self, obj):
        return obj.get_features_list()


# ===============================================================================
# SERIALIZERS FORFAITS CLIENTS
# ===============================================================================

class ForfaitSerializer(serializers.ModelSerializer):
    """Serializer pour les forfaits clients"""
    
    class Meta:
        model = Forfait
        fields = [
            'id', 'name', 'description', 'monthly_price', 'max_priority_orders',
            'discount_rate', 'can_schedule_delivery', 'can_track_realtime',
            'can_contact_driver', 'priority_support', 'is_active'
        ]
        read_only_fields = ['id']


class ClientForfaitSerializer(serializers.ModelSerializer):
    """Serializer pour les forfaits des clients"""
    forfait_details = ForfaitSerializer(source='forfait', read_only=True)
    is_active_bool = serializers.SerializerMethodField()
    days_until_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = ClientForfait
        fields = [
            'id', 'user', 'forfait', 'forfait_details', 'start_date',
            'expiration_date', 'status', 'auto_renew', 'is_active_bool',
            'days_until_expiry', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']
    
    def get_is_active_bool(self, obj):
        return obj.is_active()
    
    def get_days_until_expiry(self, obj):
        from django.utils import timezone
        delta = (obj.expiration_date.date() - timezone.now().date()).days
        return max(0, delta)


# ===============================================================================
# SERIALIZERS PAYOUTS
# ===============================================================================

class PayoutSerializer(serializers.ModelSerializer):
    """Serializer pour les payouts (paiements automatiques)"""
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    payout_type_display = serializers.CharField(source='get_payout_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    amount_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Payout
        fields = [
            'id', 'user', 'user_phone', 'user_name', 'order', 'payout_type',
            'payout_type_display', 'amount', 'amount_display', 'status',
            'status_display', 'flutterwave_payout_id', 'reason', 'created_at',
            'paid_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'user_phone', 'user_name', 'payout_type_display',
            'status_display', 'created_at', 'paid_at', 'updated_at'
        ]
    
    def get_amount_display(self, obj):
        return f"{obj.amount} FCFA"


# ===============================================================================
# SERIALIZERS CALLBACK LOGS
# ===============================================================================

class PaymentCallbackLogSerializer(serializers.ModelSerializer):
    """Serializer pour les logs de callbacks Flutterwave"""
    
    class Meta:
        model = PaymentCallbackLog
        fields = [
            'id', 'received_at', 'order', 'status_code', 'raw_data',
            'signature_valid', 'processed'
        ]
        read_only_fields = ['id', 'received_at']