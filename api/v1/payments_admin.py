"""
Admin API views for payment logs and payouts management
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from django.db.models import Q
from django.utils import timezone

from payments.models import PaymentCallbackLog, Payout
from orders.models import Order
from users.models import User


class IsPlatformAdmin(permissions.BasePermission):
    """Allow access to staff or explicit admin user_type."""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


# ============================================================================
# SERIALIZERS
# ============================================================================

class PaymentCallbackLogSerializer(serializers.ModelSerializer):
    """Serializer pour PaymentCallbackLog (read-only)"""
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    processed_display = serializers.SerializerMethodField()
    signature_valid_display = serializers.SerializerMethodField()
    
    class Meta:
        model = PaymentCallbackLog
        fields = '__all__'
        read_only_fields = '__all__'
    
    def get_processed_display(self, obj):
        return 'Traité' if obj.processed else 'Non traité'
    
    def get_signature_valid_display(self, obj):
        return 'Valide' if obj.signature_valid else 'Invalide'


class PayoutSerializer(serializers.ModelSerializer):
    """Serializer pour Payout"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    payout_type_display = serializers.CharField(source='get_payout_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Payout
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'paid_at')


# ============================================================================
# PAYMENT CALLBACK LOG ENDPOINTS
# ============================================================================

class PaymentCallbackLogListView(APIView):
    """GET /admin/payment-callbacks/ - Liste des logs callbacks"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        order_id = request.query_params.get('order_id')
        processed = request.query_params.get('processed')
        signature_valid = request.query_params.get('signature_valid')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        transaction_id = request.query_params.get('transaction_id')
        
        logs = PaymentCallbackLog.objects.select_related('order').all()
        
        if order_id:
            logs = logs.filter(order_id=order_id)
        if processed is not None:
            logs = logs.filter(processed=processed.lower() == 'true')
        if signature_valid is not None:
            logs = logs.filter(signature_valid=signature_valid.lower() == 'true')
        if date_from:
            logs = logs.filter(received_at__gte=date_from)
        if date_to:
            logs = logs.filter(received_at__lte=date_to)
        if transaction_id:
            # Rechercher dans raw_data JSON
            logs = logs.filter(raw_data__icontains=transaction_id)
        
        logs = logs.order_by('-received_at')
        serializer = PaymentCallbackLogSerializer(logs, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': logs.count()
        })


class PaymentCallbackLogDetailView(APIView):
    """GET /admin/payment-callbacks/<id>/ - Détail d'un log callback"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request, log_id):
        try:
            log = PaymentCallbackLog.objects.select_related('order').get(id=log_id)
            serializer = PaymentCallbackLogSerializer(log)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except PaymentCallbackLog.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Log introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# PAYOUT ENDPOINTS
# ============================================================================

class PayoutListView(APIView):
    """GET /admin/payouts/ - Liste des payouts généraux"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        user_id = request.query_params.get('user_id')
        payout_type = request.query_params.get('payout_type')
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        payouts = Payout.objects.select_related('user', 'order').all()
        
        if user_id:
            payouts = payouts.filter(user_id=user_id)
        if payout_type:
            payouts = payouts.filter(payout_type=payout_type)
        if status_filter:
            payouts = payouts.filter(status=status_filter)
        if date_from:
            payouts = payouts.filter(created_at__gte=date_from)
        if date_to:
            payouts = payouts.filter(created_at__lte=date_to)
        
        payouts = payouts.order_by('-created_at')
        serializer = PayoutSerializer(payouts, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': payouts.count()
        })


class PayoutCreateView(APIView):
    """POST /admin/payouts/ - Créer un payout"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        serializer = PayoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class PayoutUpdateView(APIView):
    """PATCH /admin/payouts/<id>/ - Modifier le statut d'un payout"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, payout_id):
        try:
            payout = Payout.objects.get(id=payout_id)
            new_status = request.data.get('status')
            flutterwave_payout_id = request.data.get('flutterwave_payout_id')
            
            if new_status:
                valid_statuses = ['pending', 'processing', 'paid', 'failed', 'cancelled']
                if new_status not in valid_statuses:
                    return Response({
                        'success': False,
                        'error': f'Statut invalide. Statuts valides: {", ".join(valid_statuses)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                payout.status = new_status
                if new_status == 'paid' and not payout.paid_at:
                    payout.paid_at = timezone.now()
            
            if flutterwave_payout_id:
                payout.flutterwave_payout_id = flutterwave_payout_id
            
            payout.save()
            serializer = PayoutSerializer(payout)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Payout.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payout introuvable'
            }, status=status.HTTP_404_NOT_FOUND)

