from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.db.models import Sum
from django.utils import timezone
from payments.models import StoreSubscription
from orders.models import Order
from delivery.models import Delivery

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
        
        # Commandes du jour
        daily_orders = Order.objects.filter(store=store, created_at__date=today)
        daily_revenue = daily_orders.exclude(status__in=['cancelled', 'refunded']).aggregate(Sum('items_total'))['items_total__sum'] or 0
        daily_commission = daily_orders.exclude(status__in=['cancelled', 'refunded']).aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
        daily_net_revenue = daily_revenue - daily_commission
        
        # Commandes en attente de traitement
        pending_orders = Order.objects.filter(store=store, status__in=['paid', 'confirmed']).count()
        
        # Commandes en cours
        ongoing_orders = Order.objects.filter(store=store, status__in=['preparing', 'ready', 'assigned', 'in_transit']).count()

        pending_order_list = Order.objects.filter(store=store, status__in=['paid', 'confirmed']).order_by('-created_at')[:20]
        pending_payload = []
        for o in pending_order_list:
            pending_payload.append({
                'id': o.id,
                'order_number': o.order_number,
                'client_name': o.client.get_full_name() or o.client.phone,
                'created_at': o.created_at,
                'total': o.total_amount,
                'status': o.status,
                'status_display': o.get_status_display(),
                'items_count': o.items.count(),
            })

        monthly_orders_qs = Order.objects.filter(store=store, created_at__date__gte=month_start).exclude(status__in=['cancelled', 'refunded'])
        monthly_orders = monthly_orders_qs.count()
        monthly_revenue = monthly_orders_qs.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        monthly_commission = monthly_orders_qs.aggregate(Sum('commission_amount'))['commission_amount__sum'] or 0
        monthly_net_revenue = monthly_revenue - monthly_commission

        # Forfait / abonnement actif
        active_subscription = StoreSubscription.objects.filter(store=store, status='active').order_by('-end_date').first()
        subscription_payload = None
        if active_subscription:
            subscription_payload = {
                'plan_name': active_subscription.plan_name,
                'status': active_subscription.status,
                'end_date': active_subscription.end_date,
                'auto_renew': active_subscription.auto_renew,
                'monthly_fee': active_subscription.monthly_fee,
            }

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
                    'daily_revenue': daily_revenue,
                    'daily_commission': daily_commission,
                    'daily_net_revenue': daily_net_revenue,
                    'daily_orders_count': daily_orders.count(),
                    'pending_orders': pending_orders,
                    'ongoing_orders': ongoing_orders
                },
                'pending_order_list': pending_payload,
                'monthly_orders': monthly_orders,
                'monthly_revenue': monthly_revenue,
                'monthly_commission': monthly_commission,
                'monthly_net_revenue': monthly_net_revenue,
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
