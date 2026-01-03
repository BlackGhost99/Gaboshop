from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from products.models import ProductCategory
from payments.models import CategoryCommission
from django.utils import timezone
from payments.models import StoreSubscription
from orders.models import Order
from delivery.models import Delivery
from orders.models import OrderItem
from decimal import Decimal

class ClientDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.user_type != 'client':
            return Response({'error': 'Accès réservé aux clients'}, status=status.HTTP_403_FORBIDDEN)

        # Stats
        total_orders = Order.objects.filter(client=user).count()
        active_orders = Order.objects.filter(
            client=user, 
            status__in=['created', 'pending_payment', 'paid', 'confirmed', 'preparing', 'ready', 'assigned', 'in_transit']
        ).count()
        
        # Dernières commandes
        recent_orders = Order.objects.filter(client=user).order_by('-created_at')[:5]
        
        # Sérialisation manuelle légère pour le dashboard
        orders_data = []
        for order in recent_orders:
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'store_name': order.store.name,
                'total_amount': order.total_amount,
                'status': order.status,
                'status_display': order.get_status_display(),
                'created_at': order.created_at,
                'items_count': order.items.count()
            })

        return Response({
            'success': True,
            'data': {
                'profile': {
                    'name': f"{user.first_name} {user.last_name}".strip() or user.username,
                    'email': user.email or '',
                    'phone': getattr(user, 'phone_number', '') or getattr(user, 'phone', ''),
                    'city': getattr(user, 'city', '') or '',
                },
                'stats': {
                    'total_orders': total_orders,
                    'active_orders': active_orders,
                },
                'recent_orders': orders_data
            }
        })

class StoreDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_store_manager():
            return Response({'error': 'Accès réservé aux gérants'}, status=status.HTTP_403_FORBIDDEN)

        # Récupérer le magasin du gérant
        try:
            store = user.managed_stores.first() # Supposons un magasin par gérant pour le MVP
        except Exception:
            store = None
            
        if not store:
            return Response({'error': 'Aucun magasin associé'}, status=status.HTTP_404_NOT_FOUND)

        # Période (Aujourd'hui)
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Commandes du jour — définir un filtre 'payées' robuste (par status ou paiement)
        from django.db.models import Q
        paid_filter = Q(payment__status__in=['success', 'completed']) | Q(status__in=['paid', 'confirmed', 'delivered', 'in_transit', 'assigned', 'ready', 'preparing'])
        daily_orders = Order.objects.filter(store=store, created_at__date=today).filter(paid_filter)

        # Somme exacte des ventes = sum(unit_price * quantity) des OrderItems liés
        subtotal_expr = ExpressionWrapper(F('unit_price') * F('quantity'), output_field=DecimalField(max_digits=12, decimal_places=2))
        daily_items_qs = OrderItem.objects.filter(order__in=daily_orders).annotate(subtotal=subtotal_expr)
        daily_ca = daily_items_qs.aggregate(s=Sum('subtotal'))['s'] or 0

        daily_commission = daily_orders.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
        daily_net_after_commission = (daily_ca - daily_commission)
        
        # Commandes en attente de traitement
        pending_orders = Order.objects.filter(store=store, status__in=['paid', 'confirmed']).count()
        
        # Commandes en cours
        ongoing_orders = Order.objects.filter(store=store, status__in=['preparing', 'ready', 'assigned', 'in_transit']).count()

        # Séparer les commandes entrantes (B2C vs B2B)
        all_pending_incoming = Order.objects.filter(store=store, status__in=['paid', 'confirmed']).order_by('-created_at')[:20]
        
        b2c_pending = []
        b2b_incoming_pending = []
        
        for o in all_pending_incoming:
            order_data = {
                'id': o.id,
                'order_number': o.order_number,
                'client_name': o.client.get_full_name() or o.client.phone,
                'created_at': o.created_at,
                'total': o.total_amount,
                'status': o.status,
                'status_display': o.get_status_display(),
                'items_count': o.items.count(),
                'is_b2b': o.is_b2b,
                'source_store_name': o.source_store.name if o.is_b2b and o.source_store else None,
            }
            if o.is_b2b:
                b2b_incoming_pending.append(order_data)
            else:
                b2c_pending.append(order_data)

        # Commandes B2B sortantes (passées par ce magasin aux grossistes)
        outgoing_b2b_orders = Order.objects.filter(source_store=store, is_b2b=True).order_by('-created_at')[:20]
        outgoing_b2b_payload = []
        for o in outgoing_b2b_orders:
            outgoing_b2b_payload.append({
                'id': o.id,
                'order_number': o.order_number,
                'wholesaler_name': o.store.name,
                'created_at': o.created_at,
                'total': o.total_amount,
                'status': o.status,
                'status_display': o.get_status_display(),
                'items_count': o.items.count(),
            })

        # Utiliser commandes payées pour métriques mensuelles (filtre robuste)
        monthly_orders_qs = Order.objects.filter(store=store, created_at__date__gte=month_start).filter(paid_filter)
        monthly_orders = monthly_orders_qs.count()
        # Calculer CA mensuel à partir des OrderItems
        monthly_items_qs = OrderItem.objects.filter(order__in=monthly_orders_qs).annotate(subtotal=subtotal_expr)
        monthly_ca = monthly_items_qs.aggregate(s=Sum('subtotal'))['s'] or 0
        monthly_commission = monthly_orders_qs.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
        monthly_net_after_commission = monthly_ca - monthly_commission

        # Weekly revenue: compute last 7 days (Mon-Sun of current week)
        # Build list of days starting from Monday
        from datetime import timedelta
        today = timezone.now().date()
        # Determine Monday of current week
        monday = today - timedelta(days=today.weekday())
        weekly_revenue_list = []
        for i in range(7):
            day = monday + timedelta(days=i)
            day_orders = Order.objects.filter(store=store, created_at__date=day).filter(paid_filter)
            # Use OrderItem subtotals per day for store CA
            day_items_qs = OrderItem.objects.filter(order__in=day_orders).annotate(subtotal=subtotal_expr)
            day_total = day_items_qs.aggregate(Sum('subtotal'))['subtotal__sum'] or 0
            # short name in French
            day_name = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'][i]
            weekly_revenue_list.append({
                'date': day.isoformat(),
                'name': day_name,
                'revenue': day_total
            })

        # Forfait / abonnement actif
        from payments.subscription_check import SubscriptionChecker
        active_subscription = StoreSubscription.objects.filter(store=store, status='active').order_by('-end_date').first()
        subscription_payload = None
        if active_subscription:
            days_until_expiry = SubscriptionChecker.get_days_until_expiry(store)
            plan_type = active_subscription.plan.plan_type if active_subscription.plan else 'free'
            subscription_payload = {
                'plan_name': active_subscription.plan_name,
                'plan_type': plan_type,
                'status': active_subscription.status,
                'end_date': active_subscription.end_date,
                'auto_renew': active_subscription.auto_renew,
                'monthly_fee': active_subscription.monthly_fee,
                'days_until_expiry': days_until_expiry,
            }
        else:
            # Pas de souscription active, probablement Free par défaut
            subscription_payload = {
                'plan_name': 'Free',
                'plan_type': 'free',
                'status': 'active',
                'end_date': None,
                'auto_renew': False,
                'monthly_fee': 0,
                'days_until_expiry': None,
            }

        # --- Breakdown par catégorie (CA et commission) ---
        # Expression pour le subtotal des OrderItems
        subtotal_expr = ExpressionWrapper(F('unit_price') * F('quantity'), output_field=DecimalField(max_digits=12, decimal_places=2))

        def compute_category_breakdown(order_qs):
            items_qs = OrderItem.objects.filter(order__in=order_qs).annotate(subtotal=subtotal_expr)
            grouped = items_qs.values('product__category__id', 'product__category__name').annotate(items_ca=Sum('subtotal')).order_by('-items_ca')
            breakdown = []
            # plan multiplier for store
            plan = store.get_current_plan()
            multiplier = Decimal(getattr(plan, 'commission_multiplier', 1)) if plan else Decimal('1')
            for g in grouped:
                cat_id = g.get('product__category__id')
                cat_name = g.get('product__category__name') or 'Autres'
                items_ca = g.get('items_ca') or Decimal('0.00')
                base_rate = None
                try:
                    if cat_id:
                        pc = ProductCategory.objects.get(id=cat_id)
                        sc = getattr(pc, 'store_category', None)
                        if sc:
                            try:
                                cc = CategoryCommission.objects.get(store_category=sc)
                                base_rate = Decimal(cc.base_rate)
                            except CategoryCommission.DoesNotExist:
                                base_rate = None
                except ProductCategory.DoesNotExist:
                    base_rate = None

                if base_rate is None:
                    base_rate = Decimal(store.commission_rate or Decimal('0.00'))

                effective_rate = (base_rate * Decimal(multiplier))
                commission_amount = (Decimal(items_ca) * effective_rate) / Decimal('100')
                breakdown.append({
                    'category_id': cat_id,
                    'category_name': cat_name,
                    'items_ca': items_ca,
                    'base_rate': str(base_rate),
                    'effective_rate': str(effective_rate),
                    'commission': commission_amount.quantize(Decimal('0.01'))
                })
            return breakdown

        category_breakdown_daily = compute_category_breakdown(daily_orders)
        category_breakdown_monthly = compute_category_breakdown(monthly_orders_qs)

        return Response({
            'success': True,
            'data': {
                'store': {
                    'name': store.name,
                    'is_open': store.is_open(),
                    'city': store.city,
                    'id': store.id,
                    'logo': request.build_absolute_uri(store.logo.url) if store.logo else None,
                },
                'owner': {
                    'email': store.manager.email or '',
                    'first_name': store.manager.first_name or '',
                    'last_name': store.manager.last_name or '',
                    'phone': getattr(store.manager, 'phone_number', '') or getattr(store.manager, 'phone', ''),
                },
                'stats': {
                    # New explicit keys
                    'daily_ca': daily_ca,
                    'daily_commission': daily_commission,
                    'daily_net_after_commission': daily_net_after_commission,
                    # Backward-compatible aliases expected by frontend
                    'daily_revenue': daily_ca,
                    'daily_net_revenue': daily_net_after_commission,
                    'daily_orders_count': daily_orders.count(),
                    'pending_orders': pending_orders,
                    'ongoing_orders': ongoing_orders
                },
                'pending_order_list': b2c_pending, # Backward compatibility for B2C
                'b2c_pending_orders': b2c_pending,
                'b2b_incoming_orders': b2b_incoming_pending,
                'b2b_outgoing_orders': outgoing_b2b_payload,
                'monthly_orders': monthly_orders,
                'monthly_ca': monthly_ca,
                'monthly_commission': monthly_commission,
                'monthly_net_after_commission': monthly_net_after_commission,
                # Backward-compatible aliases
                'monthly_revenue': monthly_ca,
                'monthly_net_revenue': monthly_net_after_commission,
                'weekly_revenue': weekly_revenue_list,
                'category_breakdown_daily': category_breakdown_daily,
                'category_breakdown_monthly': category_breakdown_monthly,
                'subscription': subscription_payload,
            }
        })

class DeliveryDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_delivery_agent():
            return Response({'error': 'Accès réservé aux livreurs'}, status=status.HTTP_403_FORBIDDEN)

        # Profil livreur
        try:
            profile = user.livreur_profile
        except Exception:
            return Response({'error': 'Profil livreur non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        # Livraison active
        active_delivery = Delivery.objects.filter(
            delivery_agent=user,
            status__in=['pending', 'assigned', 'accepted', 'picked_up', 'in_transit']
        ).first()
        
        active_delivery_data = None
        if active_delivery:
            proof = getattr(active_delivery, 'proof', None)
            active_delivery_data = {
                'id': active_delivery.id,
                'order_number': active_delivery.order.order_number,
                'store_name': active_delivery.order.store.name,
                'pickup_address': active_delivery.pickup_address,
                'delivery_address': active_delivery.delivery_address,
                'client_phone': active_delivery.order.client.phone,
                'status': active_delivery.status,
                'status_display': active_delivery.get_status_display(),
                'fee': active_delivery.agent_commission,
                'proof_status': getattr(proof, 'status', None),
                'proof_is_valid': proof.is_valid if proof else False,
                'proof_is_fully_confirmed': proof.is_fully_confirmed if proof else False,
                'client_received_status': proof.client_received_status if proof else False,
                'client_confirmation_pending': proof.client_confirmation_pending if proof else False,
                'can_complete_delivery': bool(proof and proof.is_valid)
            }

        # Stats du jour
        today = timezone.now().date()
        completed_today = Delivery.objects.filter(
            delivery_agent=user, 
            status='delivered',
            delivered_at__date=today
        )
        earnings_today = completed_today.aggregate(Sum('agent_commission'))['agent_commission__sum'] or 0

        return Response({
            'success': True,
            'data': {
                'profile': {
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'email': user.email,
                    'phone': user.phone,
                    'profile_picture': request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
                },
                'status': {
                    'is_available': profile.disponible,
                    'is_verified': profile.documents_verifies
                },
                'active_delivery': active_delivery_data,
                'stats': {
                    'completed_today': completed_today.count(),
                    'earnings_today': earnings_today,
                    'total_deliveries': profile.total_livraisons
                }
            }
        })


class DeliveryAssignedOrdersView(APIView):
    """Affiche toutes les commandes assignées au livreur (en attente ou en cours)"""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        if not user.is_delivery_agent():
            return Response({'error': 'Accès réservé aux livreurs'}, status=status.HTTP_403_FORBIDDEN)

        # Récupérer toutes les livraisons assignées au livreur
        assigned_deliveries = Delivery.objects.filter(
            delivery_agent=user,
            status__in=['assigned', 'pending', 'accepted', 'picked_up', 'in_transit']
        ).select_related('order', 'order__store', 'order__client').order_by('-created_at')
        
        deliveries_data = []
        for delivery in assigned_deliveries:
            try:
                client_name = delivery.order.client.get_display_name() if delivery.order.client else 'Unknown'
                client_phone = delivery.order.client.phone if delivery.order.client else 'N/A'
                proof = getattr(delivery, 'proof', None)
                
                deliveries_data.append({
                    'id': delivery.id,
                    'order_id': delivery.order.id,
                    'order_number': delivery.order.order_number,
                    'store_name': delivery.order.store.name,
                    'store_address': delivery.order.store.address,
                    'store_city': delivery.order.store.city,
                    'client_name': client_name or client_phone,
                    'client_phone': client_phone,
                    'pickup_address': delivery.pickup_address,
                    'delivery_address': delivery.delivery_address,
                    'estimated_duration': delivery.estimated_duration,
                    'distance': float(delivery.distance_to_store) if delivery.distance_to_store else None,
                    'status': delivery.status,
                    'status_display': delivery.get_status_display(),
                    'fee': float(delivery.agent_commission) if delivery.agent_commission else 0,
                    'items_count': delivery.order.items.count(),
                    'total_amount': float(delivery.order.total_amount),
                    'created_at': delivery.created_at,
                    'proof_status': getattr(proof, 'status', None),
                    'proof_is_valid': proof.is_valid if proof else False,
                    'proof_is_fully_confirmed': proof.is_fully_confirmed if proof else False,
                    'client_received_status': proof.client_received_status if proof else False,
                    'client_confirmation_pending': proof.client_confirmation_pending if proof else False,
                    'can_complete_delivery': bool(proof and proof.is_valid)
                })
            except Exception as e:
                print(f"❌ Erreur lors du traitement de la livraison {delivery.id}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        return Response({
            'success': True,
            'data': {
                'assigned_orders': deliveries_data,
                'total_assigned': len(deliveries_data),
                'pending_count': sum(1 for d in deliveries_data if d['status'] in ['assigned', 'pending']),
                'in_progress_count': sum(1 for d in deliveries_data if d['status'] in ['accepted', 'picked_up', 'in_transit']),
            }
        })
