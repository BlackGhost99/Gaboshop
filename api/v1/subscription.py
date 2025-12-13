"""
API endpoints pour la gestion des forfaits d'abonnement
Affiche le statut, les fonctionnalités, les limites en temps réel
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.utils import timezone
from decimal import Decimal

from payments.subscription_check import SubscriptionChecker
from payments.models import SubscriptionPlan, StoreSubscription, PaymentIntent
from datetime import timedelta
from django.utils import timezone as dj_timezone


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_subscription_status(request):
    """
    GET /api/v1/dashboard/subscription/status/
    
    Retourne le statut COMPLET du forfait du magasin en temps réel
    """
    try:
        store = request.user.store  # L'utilisateur doit être associé à un store
        
        # Récupérer l'abonnement actif
        subscription = SubscriptionChecker.get_active_subscription(store)
        plan = SubscriptionChecker.get_current_plan(store)
        
        # Statut d'expiration
        is_expired = SubscriptionChecker.is_subscription_expired(store)
        days_until_expiry = SubscriptionChecker.get_days_until_expiry(store)
        
        # Limites du plan
        current_products = store.products.count()
        max_products = plan.max_products if plan else None
        
        response_data = {
            'success': True,
            'subscription': {
                'id': subscription.id if subscription else None,
                'plan_name': plan.name if plan else 'Aucun forfait',
                'plan_type': plan.plan_type if plan else 'free',
                'is_active': SubscriptionChecker.is_subscription_active(store),
                'is_expired': is_expired,
                'status': subscription.status if subscription else 'inactive',
                'start_date': subscription.start_date if subscription else None,
                'end_date': subscription.end_date if subscription else None,
                'days_until_expiry': days_until_expiry,
                'auto_renew': subscription.auto_renew if subscription else False,
            },
            'plan': {
                'name': plan.name if plan else 'Aucun forfait',
                'price': float(plan.price) if plan else 0,
                'description': plan.description if plan else '',
            },
            'features': {
                'max_products': max_products,
                'current_products': current_products,
                'can_add_more_products': max_products is None or current_products < max_products,
                'has_statistics': plan.has_statistics if plan else False,
                'has_custom_page': plan.has_custom_page if plan else False,
                'can_sponsor_products': plan.can_sponsor_products if plan else False,
                'has_priority_support': plan.has_priority_support if plan else False,
                'priority_listing': plan.priority_listing if plan else 0,
            },
            'limits': {
                'products': {
                    'current': current_products,
                    'max': max_products,
                    'can_add_more': max_products is None or current_products < max_products,
                    'message': f"Vous avez {current_products}/{max_products if max_products else '∞'} produits" if max_products else "Produits illimités",
                }
            },
            'all_features': SubscriptionChecker.get_plan_features(store),
        }
        
        return Response(response_data)
    
    except AttributeError:
        return Response({
            'success': False,
            'error': 'Utilisateur non associé à un magasin'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_available_plans(request):
    """
    GET /api/v1/dashboard/subscription/plans/
    
    Retourne tous les plans disponibles pour comparaison
    """
    try:
        # Only store managers may purchase or view store subscription plans
        if request.user.user_type != 'store_manager':
            return Response({
                'success': False,
                'error': 'Accessible uniquement aux gérants de magasin'
            }, status=status.HTTP_403_FORBIDDEN)

        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
        
        plans_data = []
        for plan in plans:
            plans_data.append({
                'id': plan.id,
                'name': plan.name,
                'slug': plan.slug,
                'type': plan.plan_type,
                'price': float(plan.price),
                'description': plan.description,
                'features': {
                    'max_products': plan.max_products,
                    'has_statistics': plan.has_statistics,
                    'has_custom_page': plan.has_custom_page,
                    'can_sponsor_products': plan.can_sponsor_products,
                    'has_priority_support': plan.has_priority_support,
                    'priority_listing': plan.priority_listing,
                },
                'feature_list': plan.get_features_list(),
            })
        
        return Response({
            'success': True,
            'plans': plans_data,
            'count': len(plans_data)
        })
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_permission(request):
    """
    GET /api/v1/dashboard/subscription/check-permission/?action=add_product
    
    Vérifie si une action est permise selon le forfait
    Actions: add_product, statistics, customize, sponsor, priority_support
    """
    try:
        store = request.user.store
        action = request.query_params.get('action', '').lower()
        
        if not action:
            return Response({
                'success': False,
                'error': 'Paramètre action manquant'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        allowed_actions = {
            'add_product': SubscriptionChecker.check_can_add_product,
            'statistics': SubscriptionChecker.check_can_access_statistics,
            'customize': SubscriptionChecker.check_can_customize_store,
            'sponsor': SubscriptionChecker.check_can_sponsor_products,
            'priority_support': SubscriptionChecker.check_can_access_priority_support,
        }
        
        if action not in allowed_actions:
            return Response({
                'success': False,
                'error': f'Action inconnue: {action}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Essayer d'exécuter la vérification
            allowed_actions[action](store)
            
            return Response({
                'success': True,
                'allowed': True,
                'action': action,
                'message': f'L\'action "{action}" est autorisée pour votre forfait'
            })
        
        except Exception as e:
            return Response({
                'success': True,
                'allowed': False,
                'action': action,
                'message': str(e),
                'error': str(e)
            }, status=status.HTTP_403_FORBIDDEN)
    
    except AttributeError:
        return Response({
            'success': False,
            'error': 'Utilisateur non associé à un magasin'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def purchase_plan(request):
    """
    POST /api/v1/dashboard/subscription/purchase/

    Payload: { 'plan_id': <int> } or { 'plan_slug': <str> }

    Creates a PaymentIntent for the requested plan and returns a preview
    of the pending subscription and payment link (simulated).
    """
    try:
        if request.user.user_type != 'store_manager':
            return Response({'success': False, 'error': 'Accessible uniquement aux gérants de magasin'}, status=status.HTTP_403_FORBIDDEN)

        # ensure store exists
        try:
            store = request.user.store
        except AttributeError:
            return Response({'success': False, 'error': 'Utilisateur non associé à un magasin'}, status=status.HTTP_400_BAD_REQUEST)

        plan_id = request.data.get('plan_id')
        plan_slug = request.data.get('plan_slug')

        plan = None
        if plan_id:
            plan = SubscriptionPlan.objects.filter(id=plan_id, is_active=True).first()
        elif plan_slug:
            plan = SubscriptionPlan.objects.filter(slug=plan_slug, is_active=True).first()
        else:
            return Response({'success': False, 'error': 'plan_id ou plan_slug requis'}, status=status.HTTP_400_BAD_REQUEST)

        if not plan:
            return Response({'success': False, 'error': 'Plan introuvable ou inactif'}, status=status.HTTP_404_NOT_FOUND)

        # Create a PaymentIntent (simulated) — amount in FCFA (integer)
        try:
            amount = int(plan.price)
        except Exception:
            amount = int(Decimal(plan.price))

        intent = PaymentIntent.objects.create(
            user=request.user,
            amount=amount,
            currency='XAF',
            provider='simulated',
            status='WAITING',
            payment_url=f'https://payments.example.test/intent/{request.user.id}/{plan.slug}'
        )

        # Create a pending StoreSubscription preview (not activated until payment)
        today = dj_timezone.now().date()
        preview = {
            'store_id': store.id,
            'plan': {
                'id': plan.id,
                'name': plan.name,
                'slug': plan.slug,
                'price': float(plan.price),
            },
            'monthly_fee': float(plan.price),
            'status': 'pending_payment',
            'start_date': str(today),
            'end_date': str(today + timedelta(days=30))
        }

        return Response({
            'success': True,
            'message': 'Intent de paiement créé',
            'payment_intent': {
                'id': intent.id,
                'reference': intent.reference,
                'amount': intent.amount,
                'currency': intent.currency,
                'payment_url': intent.payment_url,
                'status': intent.status,
            },
            'subscription_preview': preview
        })

    except Exception as e:
        return Response({'success': False, 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
