"""Orders Management API for admin dashboard."""

from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from delivery.models import Delivery
from stores.models import Store
from users.models import User
from core.validators import is_valid_order_transition, can_user_change_order_status, is_valid_delivery_transition
from core.models import AuditLog


class IsPlatformAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


class OrderStatsView(APIView):
    """Statistiques rapides des commandes"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        today = timezone.now().date()
        
        stats = {
            "today": {
                "total_orders": Order.objects.filter(created_at__date=today).count(),
                "pending_payment": Order.objects.filter(created_at__date=today, status='pending').count(),
                "confirmed": Order.objects.filter(created_at__date=today, status='confirmed').count(),
                "in_preparation": Order.objects.filter(created_at__date=today, status='preparing').count(),
                "assigned": Order.objects.filter(created_at__date=today, status='assigned').count(),
                "in_delivery": Order.objects.filter(created_at__date=today, status='in_delivery').count(),
                "delivered": Order.objects.filter(created_at__date=today, status='delivered').count(),
                "cancelled": Order.objects.filter(created_at__date=today, status='cancelled').count(),
                "total_revenue": float(Order.objects.filter(created_at__date=today).aggregate(Sum('total_amount'))['total_amount__sum'] or 0),
                "delivery_fees": float(Order.objects.filter(created_at__date=today).aggregate(Sum('delivery_fee'))['delivery_fee__sum'] or 0),
            },
            "week": {
                "total_orders": Order.objects.filter(created_at__date__gte=today - timedelta(days=7)).count(),
                "delivered": Order.objects.filter(created_at__date__gte=today - timedelta(days=7), status='delivered').count(),
                "cancelled": Order.objects.filter(created_at__date__gte=today - timedelta(days=7), status='cancelled').count(),
            },
            "month": {
                "total_orders": Order.objects.filter(created_at__date__gte=today.replace(day=1)).count(),
                "delivered": Order.objects.filter(created_at__date__gte=today.replace(day=1), status='delivered').count(),
            }
        }
        
        return Response({"success": True, "data": stats})


class OrdersListView(APIView):
    """Liste des commandes avec filtres avancés"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        queryset = Order.objects.select_related('client', 'store', 'delivery__delivery_agent').all()
        
        # Filtres
        status_filter = request.query_params.get('status')
        city_filter = request.query_params.get('city')
        store_filter = request.query_params.get('store_id')
        date_range = request.query_params.get('date_range', 'all')
        payment_method = request.query_params.get('payment_method')
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if city_filter:
            queryset = queryset.filter(city=city_filter)
        
        if store_filter:
            queryset = queryset.filter(store_id=store_filter)
        
        if payment_method:
            queryset = queryset.filter(payment__payment_method=payment_method)
        
        # Filtres date
        today = timezone.now().date()
        if date_range == 'today':
            queryset = queryset.filter(created_at__date=today)
        elif date_range == 'week':
            queryset = queryset.filter(created_at__date__gte=today - timedelta(days=7))
        elif date_range == 'month':
            queryset = queryset.filter(created_at__date__gte=today.replace(day=1))
        
        orders = queryset[:100]
        
        data = [
            {
                "id": o.id,
                "order_number": o.order_number,
                "client_name": o.client.first_name + " " + o.client.last_name if o.client else "N/A",
                "client_phone": o.client.phone if o.client else "N/A",
                "total_amount": float(o.total_amount),
                "payment_status": o.payment.get_status_display() if hasattr(o, 'payment') else "N/A",
                "store_name": o.store.name if o.store else "N/A",
                "city": o.city,
                "status": o.get_status_display(),
                "delivery_agent": o.delivery.delivery_agent.username if o.delivery and o.delivery.delivery_agent else "Non assigné",
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ]
        
        return Response({"success": True, "data": data})


class OrderDetailView(APIView):
    """Détails complets d'une commande"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request, order_id):
        try:
            order = Order.objects.select_related(
                'client', 'store', 'delivery__delivery_agent'
            ).get(id=order_id)
            
            # Produits
            products = order.items.all() if hasattr(order, 'items') else []
            
            # Statut paiement
            payment = order.payment if hasattr(order, 'payment') else None
            
            # Livraison
            delivery = order.delivery if hasattr(order, 'delivery') else None
            
            data = {
                "id": order.id,
                "order_number": order.order_number,
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat(),
                "client": {
                    "name": f"{order.client.first_name} {order.client.last_name}",
                    "phone": order.client.phone,
                    "email": order.client.email,
                },
                "delivery_address": {
                    "address": order.delivery_address or "N/A",
                    "city": order.city,
                    "zone": order.delivery_zone or "N/A",
                },
                "store": {
                    "id": order.store.id,
                    "name": order.store.name,
                    "manager": order.store.manager.username if order.store.manager else "N/A",
                },
                "items": [
                    {
                        "product_name": item.product.name if hasattr(item, 'product') else "N/A",
                        "quantity": item.quantity if hasattr(item, 'quantity') else 0,
                        "unit_price": float(item.unit_price) if hasattr(item, 'unit_price') else 0,
                        "total": float(item.total_price) if hasattr(item, 'total_price') else 0,
                    }
                    for item in products
                ],
                "payment": {
                    "method": payment.get_payment_method_display() if payment else "N/A",
                    "status": payment.get_status_display() if payment else "N/A",
                    "amount": float(payment.amount) if payment else 0,
                    "reference": payment.transaction_id if payment else "N/A",
                },
                "delivery": {
                    "agent": delivery.delivery_agent.username if delivery and delivery.delivery_agent else "Non assigné",
                    "status": delivery.get_status_display() if delivery else "N/A",
                    "distance_km": float(delivery.distance_to_store) if delivery else 0,
                    "fee_charged": float(order.delivery_fee),
                },
                "totals": {
                    "subtotal": float(order.subtotal_amount),
                    "delivery_fee": float(order.delivery_fee),
                    "total": float(order.total_amount),
                },
                "status": order.get_status_display(),
                "order_status": order.status,
            }
            
            return Response({"success": True, "data": data})
        
        except Order.DoesNotExist:
            return Response({"success": False, "error": "Commande non trouvée"}, status=404)


class DeliveryAssignmentView(APIView):
    """Attribution des livreurs (auto ou manuel) avec validations"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request, order_id=None):
        if not order_id:
            order_id = request.data.get('order_id')
        
        delivery_agent_id = request.data.get('delivery_agent_id')
        auto_assign = request.data.get('auto_assign', False)
        
        try:
            order = Order.objects.get(id=order_id)
            
            # VALIDATION: La commande doit être en état 'ready' avant attribution
            if order.status != 'ready':
                return Response({
                    "success": False,
                    "error": f"La commande doit être prête pour livraison (actuellement: {order.get_status_display()})"
                }, status=400)
            
            if auto_assign:
                # Attribution automatique : livreur avec moins de commandes
                agent = User.objects.filter(
                    user_type='delivery_agent'
                ).annotate(
                    active_orders=Count('deliveries', filter=Q(deliveries__status__in=['assigned', 'in_transit']))
                ).order_by('active_orders').first()
                
                if not agent:
                    return Response({"success": False, "error": "Aucun livreur disponible"}, status=400)
                assignment_type = 'auto'
            else:
                # Attribution manuelle
                if not delivery_agent_id:
                    return Response({"success": False, "error": "ID livreur requis"}, status=400)
                
                agent = User.objects.get(id=delivery_agent_id, user_type='delivery_agent')
                assignment_type = 'manual'
            
            # Créer ou mettre à jour la livraison
            delivery, created = Delivery.objects.get_or_create(order=order)
            old_agent_id = delivery.delivery_agent.id if delivery.delivery_agent else None
            
            # VALIDATION: Vérifier que la transition de livraison est valide
            old_delivery_status = delivery.status
            if not is_valid_delivery_transition(old_delivery_status, 'assigned'):
                return Response({
                    "success": False,
                    "error": f"Transition de livraison invalide: {delivery.get_status_display()} → Livreur assigné"
                }, status=400)
            
            delivery.delivery_agent = agent
            delivery.status = 'assigned'  # Livreur assigné, en attente d'acceptation
            delivery.is_auto_assigned = auto_assign
            delivery.save()
            
            # Mettre à jour le statut de la commande (valider la transition)
            if not is_valid_order_transition(order.status, 'assigned'):
                return Response({
                    "success": False,
                    "error": f"Transition de commande invalide: {order.get_status_display()} → Livreur assigné"
                }, status=400)
            
            order.status = 'assigned'
            order.save()
            
            # LOGGING: Enregistrer l'attribution
            AuditLog.log_action(
                action_type='delivery_assigned',
                user=request.user,
                object_type='delivery',
                object_id=delivery.id,
                old_value=f"agent_{old_agent_id}" if old_agent_id else "unassigned",
                new_value=f"agent_{agent.id}",
                reason=f"Assignment {assignment_type} par {request.user.username}",
            )
            
            # Envoyer notification au livreur
            try:
                from notifications.models import Notification
                Notification.objects.create(
                    user=agent,
                    title='Nouvelle commande assignée',
                    body=f'Vous avez reçu une nouvelle commande #{order.order_number} de {order.store.name}',
                    notif_type='delivery',
                    related_order=order
                )
            except Exception as e:
                print(f"Erreur création notification: {e}")
            
            return Response({
                "success": True,
                "message": f"Livreur {agent.username} assigné avec succès ({assignment_type})",
                "data": {
                    "order_id": order.id,
                    "delivery_agent": agent.username,
                    "status": "assigned",
                    "is_auto_assigned": auto_assign,
                }
            })
        
        except Order.DoesNotExist:
            return Response({"success": False, "error": "Commande non trouvée"}, status=404)
        except User.DoesNotExist:
            return Response({"success": False, "error": "Livreur non trouvé"}, status=404)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=500)


class OrderStatusUpdateView(APIView):
    """Mise à jour du statut d'une commande avec validations strictes"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
            new_status = request.data.get('status')
            reason = request.data.get('reason', '')
            
            if not new_status:
                return Response({"success": False, "error": "Statut requis"}, status=400)
            
            # VALIDATION 1: Vérifier que c'est une transition valide
            if not is_valid_order_transition(order.status, new_status):
                return Response({
                    "success": False,
                    "error": f"Transition invalide: {order.get_status_display()} → {Order._meta.get_field('status').choices[next(i for i, (k, v) in enumerate(Order._meta.get_field('status').choices) if k == new_status)][1]}"
                }, status=400)
            
            # VALIDATION 2: Vérifier les permissions de l'utilisateur
            is_allowed, error_msg = can_user_change_order_status(request.user, order.status, new_status)
            if not is_allowed:
                return Response({"success": False, "error": error_msg}, status=403)
            
            old_status = order.status
            order.status = new_status
            order.save()
            
            # LOGGING: Enregistrer le changement dans l'audit trail
            AuditLog.log_action(
                action_type='order_status_change',
                user=request.user,
                object_type='order',
                object_id=order.id,
                old_value=old_status,
                new_value=new_status,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                reason=reason,
            )
            
            return Response({
                "success": True,
                "message": f"Statut mis à jour à {order.get_status_display()}",
                "data": {
                    "order_id": order.id,
                    "old_status": old_status,
                    "new_status": order.status,
                    "status_display": order.get_status_display(),
                }
            })
        
        except Order.DoesNotExist:
            return Response({"success": False, "error": "Commande non trouvée"}, status=404)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=500)
    
    def get_client_ip(self, request):
        """Récupère l'IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class OrdersCancelView(APIView):
    """Annulation d'une commande"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
            reason = request.data.get('reason', 'Annulation admin')
            
            order.status = 'cancelled'
            order.save()
            
            # TODO: Logique de remboursement
            
            return Response({
                "success": True,
                "message": "Commande annulée",
                "reason": reason,
            })
        
        except Order.DoesNotExist:
            return Response({"success": False, "error": "Commande non trouvée"}, status=404)


class OrdersByStoreView(APIView):
    """Statistiques des commandes par magasin"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        today = timezone.now().date()
        
        stores = Store.objects.all()
        
        data = []
        for store in stores:
            today_orders = Order.objects.filter(store=store, created_at__date=today)
            
            data.append({
                "store_id": store.id,
                "store_name": store.name,
                "pending": today_orders.filter(status__in=['pending', 'confirmed']).count(),
                "preparing": today_orders.filter(status='preparing').count(),
                "problematic": today_orders.filter(status='cancelled').count(),
                "total_today": today_orders.count(),
                "total_month": Order.objects.filter(store=store, created_at__date__gte=today.replace(day=1)).count(),
            })
        
        return Response({"success": True, "data": data})


class DeliveryAgentStatsView(APIView):
    """Statistiques des commandes par livreur"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        today = timezone.now().date()
        
        agents = User.objects.filter(user_type='delivery_agent')
        
        data = []
        for agent in agents:
            deliveries = Delivery.objects.filter(delivery_agent=agent)
            today_deliveries = deliveries.filter(created_at__date=today)
            
            total_earnings = 0  # À calculer depuis DeliveryPayout
            
            data.append({
                "id": agent.id,
                "agent_id": agent.id,
                "name": agent.get_display_name() or agent.username,
                "agent_name": agent.username,
                "email": agent.email,
                "phone": agent.phone,
                "contact": agent.phone,
                "assigned": today_deliveries.filter(status='assigned').count(),
                "active_orders": today_deliveries.filter(status__in=['assigned', 'in_transit']).count(),
                "in_transit": today_deliveries.filter(status='in_transit').count(),
                "delivered": today_deliveries.filter(status='delivered').count(),
                "cancelled": today_deliveries.filter(status='cancelled').count(),
                "total_today": today_deliveries.count(),
                "total_earnings": total_earnings,
                "status": "active",
            })
        
        return Response({"success": True, "data": data})
