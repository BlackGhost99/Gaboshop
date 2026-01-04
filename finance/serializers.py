"""
Finance serializers
"""
from rest_framework import serializers
from .models import Supplier, Expense
from orders.models import Order


class SupplierSerializer(serializers.ModelSerializer):
    """Serializer pour les fournisseurs"""
    
    class Meta:
        model = Supplier
        fields = [
            'id', 'name', 'contact_person', 'phone', 'email',
            'address', 'notes', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ExpenseSerializer(serializers.ModelSerializer):
    """Serializer pour les dépenses"""
    supplier_display = serializers.CharField(source='get_supplier_display', read_only=True)
    created_by_name = serializers.SerializerMethodField()
    b2b_order_number = serializers.CharField(source='b2b_order.order_number', read_only=True)
    
    class Meta:
        model = Expense
        fields = [
            'id', 'expense_type', 'supplier', 'supplier_name', 'supplier_display',
            'reference', 'b2b_order', 'b2b_order_number', 'amount', 'currency',
            'expense_date', 'payment_method', 'payment_status', 'notes',
            'attachment', 'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'b2b_order', 'created_by', 'created_at', 'updated_at']
    
    def get_created_by_name(self, obj):
        if obj.created_by:
            return f"{obj.created_by.first_name} {obj.created_by.last_name}"
        return None


class SalesSerializer(serializers.ModelSerializer):
    """Serializer pour les ventes (Orders)"""
    client_name = serializers.SerializerMethodField()
    net_amount = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'client_name', 'created_at',
            'items_total', 'commission_amount', 'service_fee',
            'delivery_fee', 'total_amount', 'net_amount',
            'status', 'status_display', 'is_b2b'
        ]
    
    def get_client_name(self, obj):
        if obj.client:
            return f"{obj.client.first_name} {obj.client.last_name}"
        return "—"
    
    def get_net_amount(self, obj):
        """Montant net reçu par le store"""
        return obj.items_total - obj.commission_amount - obj.service_fee


class SalesSummarySerializer(serializers.Serializer):
    """Serializer pour le résumé des ventes"""
    gross_sales = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_commission = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_service_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_delivery_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    net_received = serializers.DecimalField(max_digits=12, decimal_places=2)
    orders_count = serializers.IntegerField()
    refunds_total = serializers.DecimalField(max_digits=12, decimal_places=2)


class ExpensesSummarySerializer(serializers.Serializer):
    """Serializer pour le résumé des dépenses"""
    expenses_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    expenses_count = serializers.IntegerField()
