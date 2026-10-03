from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from .models import Order, OrderItem
from products.models import Product

class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_image = serializers.ImageField(source='product.image', read_only=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = [
            'id', 'product', 'product_name', 'product_image',
            'quantity', 'unit_price', 'subtotal'
        ]
        read_only_fields = ['unit_price', 'subtotal']

class OrderItemCreateSerializer(serializers.Serializer):
    """Serializer pour la création d'items de commande"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    
    def validate(self, attrs):
        product_id = attrs['product_id']
        quantity = attrs['quantity']
        
        try:
            product = Product.objects.get(id=product_id, is_available=True)
        except Product.DoesNotExist:
            raise serializers.ValidationError({
                'product_id': _('Produit non disponible.')
            })
        
        # Vérifier le stock
        if not product.check_stock(quantity):
            raise serializers.ValidationError({
                'quantity': _(f'Stock insuffisant. Il reste {product.stock} unité(s).')
            })
        
        attrs['product'] = product
        attrs['unit_price'] = product.price
        
        return attrs

class OrderSerializer(serializers.ModelSerializer):
    """Serializer pour les commandes"""
    items = OrderItemSerializer(many=True, read_only=True)
    store_name = serializers.CharField(source='store.name', read_only=True)
    store_zone = serializers.CharField(source='store.zone', read_only=True)
    client_phone = serializers.CharField(source='client.phone', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    delivery_id = serializers.SerializerMethodField()
    delivery_status = serializers.SerializerMethodField()
    client_received_status = serializers.SerializerMethodField()
    client_confirmation_pending = serializers.SerializerMethodField()
    client_can_confirm = serializers.SerializerMethodField()
    invoice_breakdown = serializers.SerializerMethodField()
    payment_arrangement = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'id', 'order_number', 'client', 'client_phone', 'store', 'store_name', 'store_zone',
            'status', 'status_display', 'items_total', 'delivery_fee', 'delivery_cost', 'delivery_requested', 'vehicle_type', 'operator_fee', 'tax_amount', 'payment_fees',
            'total_amount', 'city', 'delivery_address', 'delivery_phone', 'delivery_zone',
            'notes', 'items', 'created_at', 'updated_at', 'confirmed_at', 'delivered_at',
            'delivery_id', 'delivery_status', 'client_received_status', 'client_confirmation_pending', 'client_can_confirm',
            'invoice_breakdown', 'payment_arrangement'
        ]
        read_only_fields = [
            'id', 'order_number', 'client', 'items_total', 'total_amount', 'operator_fee', 'payment_fees',
            'created_at', 'updated_at', 'confirmed_at', 'delivered_at',
            'delivery_id', 'delivery_status', 'client_received_status', 'client_confirmation_pending', 'client_can_confirm',
            'invoice_breakdown', 'payment_arrangement', 'delivery_cost', 'vehicle_type'
        ]

    def _get_delivery(self, obj):
        return getattr(obj, 'delivery', None)

    def get_delivery_id(self, obj):
        delivery = self._get_delivery(obj)
        return delivery.id if delivery else None

    def get_delivery_status(self, obj):
        delivery = self._get_delivery(obj)
        return delivery.status if delivery else None

    def get_client_received_status(self, obj):
        delivery = self._get_delivery(obj)
        if delivery and hasattr(delivery, 'proof'):
            return delivery.proof.client_received_status
        return False

    def get_client_confirmation_pending(self, obj):
        delivery = self._get_delivery(obj)
        if delivery and hasattr(delivery, 'proof'):
            return delivery.proof.client_confirmation_pending
        return False

    def get_client_can_confirm(self, obj):
        delivery = self._get_delivery(obj)
        if not delivery or not hasattr(delivery, 'proof'):
            return False
        return obj.status == 'delivered' and delivery.proof.client_confirmation_pending

    def get_invoice_breakdown(self, obj):
        """
        Retourne le détail complet de la facture pour le client
        Affiche chaque franc FCFA avec la ventilation complète, y compris frais opérateur
        """
        from decimal import Decimal
        
        # Construire la liste des articles avec subtotaux
        items_breakdown = []
        for item in obj.items.all():
            items_breakdown.append({
                'product_id': item.product.id,
                'product_name': item.product.name,
                'quantity': item.quantity,
                'unit_price': str(item.unit_price),
                'subtotal': str(item.subtotal)
            })
        
        # Convertir tous les montants en string pour éviter les problèmes de sérialisation
        return {
            'items': items_breakdown,
            'summary': {
                'items_total': str(obj.items_total),
                'delivery_fee': str(obj.delivery_fee),
                'delivery_cost': str(obj.delivery_cost),
                'vehicle_type': obj.vehicle_type or None,
                'operator_fee': str(obj.operator_fee),
                'tax_amount': str(obj.tax_amount),
                'payment_fees': str(obj.payment_fees),
                'total_amount': str(obj.total_amount)
            },
            'payment_breakdown': {
                'label': 'Voici le détail exact de votre paiement:',
                'lines': [
                    {
                        'description': 'Sous-total (articles)',
                        'amount': str(obj.items_total),
                        'currency': 'FCFA'
                    },
                    {
                        'description': 'Frais de livraison (calculé selon véhicule)',
                        'amount': str(obj.delivery_cost),
                        'currency': 'FCFA'
                    },
                    {
                        'description': 'Type de véhicule',
                        'amount': obj.vehicle_type or '',
                        'currency': ''
                    },
                    *([{
                        'description': 'Frais opérateur Mobile Money (Airtel/Moov)',
                        'amount': str(obj.operator_fee),
                        'currency': 'FCFA'
                    }] if obj.operator_fee > 0 else []),
                    *([{
                        'description': 'Taxes',
                        'amount': str(obj.tax_amount),
                        'currency': 'FCFA'
                    }] if obj.tax_amount > 0 else []),
                    *([{
                        'description': 'Frais de transaction (Mobile Money)',
                        'amount': str(obj.payment_fees),
                        'currency': 'FCFA'
                    }] if obj.payment_fees > 0 else []),
                    {
                        'description': 'TOTAL A PAYER',
                        'amount': str(obj.total_amount),
                        'currency': 'FCFA',
                        'is_total': True
                    }
                ]
            }
        }

    def get_payment_arrangement(self, obj):
        from payments.direct_service import payment_summary
        return payment_summary(obj, self.context.get('request'))

class OrderCreateSerializer(serializers.ModelSerializer):
    """Serializer pour la création de commande"""
    items = OrderItemCreateSerializer(many=True, write_only=True)
    delivery_type = serializers.ChoiceField(
        choices=['standard', 'express'],
        default='standard',
        required=False,
        allow_blank=False
    )
    delivery_requested = serializers.BooleanField(
        default=True,
        required=False
    )
    notes = serializers.CharField(
        default='',
        required=False,
        allow_blank=True
    )
    city = serializers.CharField(
        default='Libreville',
        required=False,
        allow_blank=False
    )
    payment_flow = serializers.CharField(write_only=True)
    payment_method = serializers.CharField(write_only=True)
    delivery_payment_method = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Order
        fields = [
            'store', 'city', 'delivery_address', 'delivery_phone', 'delivery_zone',
            'delivery_type', 'delivery_requested', 'notes', 'items',
            'payment_flow', 'payment_method', 'delivery_payment_method'
        ]
    
    def validate(self, attrs):
        store = attrs['store']
        items = attrs['items']
        from payments.configuration import available_payment_options
        _, options = available_payment_options(store, attrs.get('delivery_requested', True))
        if not any(option['flow'] == attrs.get('payment_flow') and option['method'] == attrs.get('payment_method') for option in options):
            raise serializers.ValidationError({'payment_method': _('Ce circuit ou moyen de paiement n’est pas autorisé.')})

        from payments.subscription_check import SubscriptionChecker
        
        # Vérifier que le magasin est actif
        if not store.is_active:
            raise serializers.ValidationError({
                'store': _('Ce magasin n\'est pas actif.')
            })
        
        # Vérifier les heures d'ouverture
        if not store.is_open():
            raise serializers.ValidationError({
                'store': _('Ce magasin est actuellement fermé.')
            })
        
        # Vérifier la limite de commandes mensuelles
        try:
            SubscriptionChecker.check_can_create_order(store)
        except PermissionDenied as e:
            raise serializers.ValidationError({'store': str(e)})

        # Vérifier qu'il y a des articles
        if not items:
            raise serializers.ValidationError({
                'items': _('La commande doit contenir au moins un article.')
            })
        
        # Calculer le total et vérifier le montant minimum
        total = sum(item['unit_price'] * item['quantity'] for item in items)
        if total < store.min_order_amount:
            raise serializers.ValidationError({
                'items': _(f'Le montant minimum de commande est {store.min_order_amount} FCFA.')
            })
        
        delivery_type = attrs.get('delivery_type', 'standard')
        if delivery_type == 'express':
            try:
                SubscriptionChecker.check_can_offer_express_delivery(store)
            except PermissionDenied as e:
                raise serializers.ValidationError({'delivery_type': str(e)})

        attrs['items_total'] = total
        attrs['delivery_fee'] = store.delivery_fee_express if delivery_type == 'express' else store.delivery_fee
        attrs['total_amount'] = total + attrs['delivery_fee']
        
        return attrs
    
    def create(self, validated_data):
        items_data = validated_data.pop('items')
        payment_flow = validated_data.pop('payment_flow')
        payment_method = validated_data.pop('payment_method')
        delivery_payment_method = validated_data.pop('delivery_payment_method', '')
        request = self.context.get('request')
        
        # Créer la commande
        order = Order.objects.create(
            client=request.user,
            **validated_data
        )
        
        # Créer les OrderItems
        for item_data in items_data:
            OrderItem.objects.create(
                order=order,
                product=item_data['product'],
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price']
            )
        
        # Réduire les stocks
        for item_data in items_data:
            item_data['product'].reduce_stock(item_data['quantity'])
        
        # Recalculate totals (commission depends on created OrderItems)
        operator = 'moov' if payment_method == 'moov_money' else 'airtel'
        order.calculate_totals(operator=operator, payment_method=payment_method)

        from payments.direct_service import create_arrangement
        create_arrangement(order, payment_flow, payment_method, delivery_payment_method, request.user)
        return order

class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer pour la mise à jour du statut de commande"""
    class Meta:
        model = Order
        fields = ['status']
    
    def validate_status(self, value):
        # Transitions alignées avec ORDER_STATUS_CHOICES
        valid_transitions = {
            'created': ['pending_payment', 'cancelled'],
            'pending_payment': ['paid', 'cancelled'],
            'paid': ['confirmed', 'cancelled'],
            'confirmed': ['preparing', 'cancelled'],
            'preparing': ['ready', 'cancelled'],
            'ready': ['assigned', 'cancelled'],
            'assigned': ['in_transit', 'cancelled'],
            'in_transit': ['delivered', 'cancelled'],
            'delivered': [],
            'cancelled': [],
            'refunded': [],
        }
        
        current_status = self.instance.status
        if value not in valid_transitions.get(current_status, []):
            raise serializers.ValidationError(
                _(f'Transition invalide: {current_status} ? {value}')
            )
        
        return value
