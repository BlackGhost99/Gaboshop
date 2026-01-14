"""
Admin API views for subscription plans management (B2C and B2B)
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from payments.models import SubscriptionPlan, StoreSubscription
from b2b.models import B2BSubscriptionPlan, B2BStoreSubscription
from stores.models import Store
from users.models import User


class IsPlatformAdmin(permissions.BasePermission):
    """Allow access to staff or explicit admin user_type."""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


# ============================================================================
# SERIALIZERS
# ============================================================================

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for SubscriptionPlan (B2C)"""
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_features(self, obj):
        return obj.get_features_list()


class B2BSubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for B2BSubscriptionPlan"""
    features = serializers.SerializerMethodField()
    
    class Meta:
        model = B2BSubscriptionPlan
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_features(self, obj):
        return obj.get_all_features()


class StoreSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for StoreSubscription"""
    store_name = serializers.CharField(source='store.name', read_only=True)
    plan_name_display = serializers.SerializerMethodField()
    is_active_display = serializers.SerializerMethodField()
    
    class Meta:
        model = StoreSubscription
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'start_date')
    
    def get_plan_name_display(self, obj):
        return obj.plan.name if obj.plan else obj.plan_name
    
    def get_is_active_display(self, obj):
        return obj.is_active()


class B2BStoreSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for B2BStoreSubscription"""
    store_name = serializers.CharField(source='store.name', read_only=True)
    plan_name_display = serializers.SerializerMethodField()
    is_active_display = serializers.SerializerMethodField()
    
    class Meta:
        model = B2BStoreSubscription
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_plan_name_display(self, obj):
        return obj.plan.name if obj.plan else obj.plan_name
    
    def get_is_active_display(self, obj):
        return obj.is_active()


# ============================================================================
# SUBSCRIPTION PLAN (B2C) ENDPOINTS
# ============================================================================

class SubscriptionPlanListView(APIView):
    """GET /admin/subscription-plans/ - Liste des plans B2C"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        plans = SubscriptionPlan.objects.all().order_by('price')
        serializer = SubscriptionPlanSerializer(plans, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': plans.count()
        })


class SubscriptionPlanCreateView(APIView):
    """POST /admin/subscription-plans/ - Créer un plan B2C"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        serializer = SubscriptionPlanSerializer(data=request.data)
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


class SubscriptionPlanDetailView(APIView):
    """GET /admin/subscription-plans/<id>/ - Détail d'un plan B2C"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request, plan_id):
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
            serializer = SubscriptionPlanSerializer(plan)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Plan introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


class SubscriptionPlanUpdateView(APIView):
    """PATCH /admin/subscription-plans/<id>/ - Modifier un plan B2C"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, plan_id):
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
            serializer = SubscriptionPlanSerializer(plan, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'data': serializer.data
                })
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Plan introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


class SubscriptionPlanDeleteView(APIView):
    """DELETE /admin/subscription-plans/<id>/ - Supprimer un plan B2C"""
    permission_classes = [IsPlatformAdmin]
    
    def delete(self, request, plan_id):
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id)
            # Vérifier qu'aucun store n'utilise ce plan
            active_subscriptions = StoreSubscription.objects.filter(plan=plan, status='active').count()
            if active_subscriptions > 0:
                return Response({
                    'success': False,
                    'error': f'Impossible de supprimer: {active_subscriptions} abonnement(s) actif(s) utilisent ce plan'
                }, status=status.HTTP_400_BAD_REQUEST)
            plan.delete()
            return Response({
                'success': True,
                'message': 'Plan supprimé avec succès'
            })
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Plan introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# B2B SUBSCRIPTION PLAN ENDPOINTS
# ============================================================================

class B2BSubscriptionPlanListView(APIView):
    """GET /admin/b2b-subscription-plans/ - Liste des plans B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        plans = B2BSubscriptionPlan.objects.all().order_by('display_order', 'price')
        serializer = B2BSubscriptionPlanSerializer(plans, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': plans.count()
        })


class B2BSubscriptionPlanCreateView(APIView):
    """POST /admin/b2b-subscription-plans/ - Créer un plan B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        serializer = B2BSubscriptionPlanSerializer(data=request.data)
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


class B2BSubscriptionPlanDetailView(APIView):
    """GET /admin/b2b-subscription-plans/<id>/ - Détail d'un plan B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request, plan_id):
        try:
            plan = B2BSubscriptionPlan.objects.get(id=plan_id)
            serializer = B2BSubscriptionPlanSerializer(plan)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except B2BSubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Plan introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


class B2BSubscriptionPlanUpdateView(APIView):
    """PATCH /admin/b2b-subscription-plans/<id>/ - Modifier un plan B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, plan_id):
        try:
            plan = B2BSubscriptionPlan.objects.get(id=plan_id)
            serializer = B2BSubscriptionPlanSerializer(plan, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'data': serializer.data
                })
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except B2BSubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Plan introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


class B2BSubscriptionPlanDeleteView(APIView):
    """DELETE /admin/b2b-subscription-plans/<id>/ - Supprimer un plan B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def delete(self, request, plan_id):
        try:
            plan = B2BSubscriptionPlan.objects.get(id=plan_id)
            # Vérifier qu'aucun store n'utilise ce plan
            active_subscriptions = B2BStoreSubscription.objects.filter(plan=plan, status='active').count()
            if active_subscriptions > 0:
                return Response({
                    'success': False,
                    'error': f'Impossible de supprimer: {active_subscriptions} abonnement(s) actif(s) utilisent ce plan'
                }, status=status.HTTP_400_BAD_REQUEST)
            plan.delete()
            return Response({
                'success': True,
                'message': 'Plan supprimé avec succès'
            })
        except B2BSubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Plan introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# STORE SUBSCRIPTION (B2C) ENDPOINTS
# ============================================================================

class StoreSubscriptionListView(APIView):
    """GET /admin/store-subscriptions/ - Liste des abonnements stores"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        # Filtres
        store_id = request.query_params.get('store_id')
        plan_id = request.query_params.get('plan_id')
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        
        subscriptions = StoreSubscription.objects.select_related('store', 'plan').all()
        
        if store_id:
            subscriptions = subscriptions.filter(store_id=store_id)
        if plan_id:
            subscriptions = subscriptions.filter(plan_id=plan_id)
        if status_filter:
            subscriptions = subscriptions.filter(status=status_filter)
        if search:
            subscriptions = subscriptions.filter(
                Q(store__name__icontains=search) |
                Q(plan_name__icontains=search)
            )
        
        subscriptions = subscriptions.order_by('-created_at')
        serializer = StoreSubscriptionSerializer(subscriptions, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': subscriptions.count()
        })


class StoreSubscriptionCreateView(APIView):
    """POST /admin/store-subscriptions/ - Créer/assigner un abonnement"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        store_id = request.data.get('store_id')
        plan_id = request.data.get('plan_id')
        end_date = request.data.get('end_date')
        auto_renew = request.data.get('auto_renew', True)
        
        if not store_id:
            return Response({
                'success': False,
                'error': 'store_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Magasin introuvable'
            }, status=status.HTTP_404_NOT_FOUND)
        
        plan = None
        if plan_id:
            try:
                plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
            except SubscriptionPlan.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Plan introuvable'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Calculer end_date si non fourni (30 jours par défaut)
        if not end_date:
            end_date = (timezone.now().date() + timedelta(days=30)).isoformat()
        
        subscription_data = {
            'store': store.id,
            'plan': plan.id if plan else None,
            'plan_name': plan.name if plan else 'Free',
            'monthly_fee': plan.price if plan else 0,
            'end_date': end_date,
            'auto_renew': auto_renew,
            'status': 'active'
        }
        
        serializer = StoreSubscriptionSerializer(data=subscription_data)
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


class StoreSubscriptionUpdateView(APIView):
    """PATCH /admin/store-subscriptions/<id>/ - Modifier un abonnement"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, subscription_id):
        try:
            subscription = StoreSubscription.objects.select_related('store', 'plan').get(id=subscription_id)
            
            # Créer une copie mutable de request.data
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            
            # Si le plan change, mettre à jour automatiquement plan_name et monthly_fee
            plan_id = data.get('plan_id')
            if plan_id is not None:
                from payments.models import SubscriptionPlan
                if plan_id:
                    try:
                        plan = SubscriptionPlan.objects.get(id=plan_id)
                        # Mettre à jour plan_name et monthly_fee depuis le nouveau plan
                        data['plan_name'] = plan.name
                        data['monthly_fee'] = float(plan.price)
                        # Convertir plan_id en plan pour le serializer (le serializer attend 'plan', pas 'plan_id')
                        data['plan'] = plan_id
                    except SubscriptionPlan.DoesNotExist:
                        return Response({
                            'success': False,
                            'error': 'Plan introuvable'
                        }, status=status.HTTP_404_NOT_FOUND)
                else:
                    # Si plan_id est vide, c'est le plan Free
                    data['plan_name'] = 'Free'
                    data['monthly_fee'] = 0
                    data['plan'] = None
                
                # Supprimer plan_id car le serializer n'attend que 'plan'
                if 'plan_id' in data:
                    del data['plan_id']
            
            serializer = StoreSubscriptionSerializer(subscription, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # Recharger l'objet depuis la DB pour avoir toutes les données à jour
                subscription.refresh_from_db()
                # Réutiliser le serializer avec l'objet rafraîchi pour avoir tous les champs calculés
                updated_serializer = StoreSubscriptionSerializer(subscription)
                return Response({
                    'success': True,
                    'data': updated_serializer.data
                })
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except StoreSubscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Abonnement introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# B2B STORE SUBSCRIPTION ENDPOINTS
# ============================================================================

class B2BStoreSubscriptionListView(APIView):
    """GET /admin/b2b-store-subscriptions/ - Liste des abonnements B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        # Filtres
        store_id = request.query_params.get('store_id')
        plan_id = request.query_params.get('plan_id')
        status_filter = request.query_params.get('status')
        search = request.query_params.get('search')
        
        subscriptions = B2BStoreSubscription.objects.select_related('store', 'plan').all()
        
        if store_id:
            subscriptions = subscriptions.filter(store_id=store_id)
        if plan_id:
            subscriptions = subscriptions.filter(plan_id=plan_id)
        if status_filter:
            subscriptions = subscriptions.filter(status=status_filter)
        if search:
            subscriptions = subscriptions.filter(
                Q(store__name__icontains=search) |
                Q(plan_name__icontains=search)
            )
        
        subscriptions = subscriptions.order_by('-created_at')
        serializer = B2BStoreSubscriptionSerializer(subscriptions, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': subscriptions.count()
        })


class B2BStoreSubscriptionCreateView(APIView):
    """POST /admin/b2b-store-subscriptions/ - Créer/assigner un abonnement B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        store_id = request.data.get('store_id')
        plan_id = request.data.get('plan_id')
        end_date = request.data.get('end_date')
        auto_renew = request.data.get('auto_renew', True)
        
        if not store_id:
            return Response({
                'success': False,
                'error': 'store_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            store = Store.objects.get(id=store_id, is_b2b=True)
        except Store.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Magasin B2B introuvable'
            }, status=status.HTTP_404_NOT_FOUND)
        
        plan = None
        if plan_id:
            try:
                plan = B2BSubscriptionPlan.objects.get(id=plan_id, is_active=True)
            except B2BSubscriptionPlan.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Plan introuvable'
                }, status=status.HTTP_404_NOT_FOUND)
        
        # Calculer end_date si non fourni (30 jours par défaut)
        if not end_date:
            end_date = (timezone.now().date() + timedelta(days=30)).isoformat()
        
        subscription_data = {
            'store': store.id,
            'plan': plan.id if plan else None,
            'plan_name': plan.name if plan else 'B2B Free',
            'monthly_fee': plan.price if plan else 0,
            'end_date': end_date,
            'auto_renew': auto_renew,
            'status': 'active'
        }
        
        serializer = B2BStoreSubscriptionSerializer(data=subscription_data)
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


class B2BStoreSubscriptionUpdateView(APIView):
    """PATCH /admin/b2b-store-subscriptions/<id>/ - Modifier un abonnement B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, subscription_id):
        try:
            subscription = B2BStoreSubscription.objects.select_related('store', 'plan').get(id=subscription_id)
            
            # Créer une copie mutable de request.data
            data = request.data.copy() if hasattr(request.data, 'copy') else dict(request.data)
            
            # Si le plan change, mettre à jour automatiquement plan_name et monthly_fee
            plan_id = data.get('plan_id')
            if plan_id is not None:
                if plan_id:
                    try:
                        plan = B2BSubscriptionPlan.objects.get(id=plan_id, is_active=True)
                        # Mettre à jour plan_name et monthly_fee depuis le nouveau plan
                        data['plan_name'] = plan.name
                        data['monthly_fee'] = float(plan.price)
                        # Convertir plan_id en plan pour le serializer (le serializer attend 'plan', pas 'plan_id')
                        data['plan'] = plan_id
                    except B2BSubscriptionPlan.DoesNotExist:
                        return Response({
                            'success': False,
                            'error': 'Plan introuvable'
                        }, status=status.HTTP_404_NOT_FOUND)
                else:
                    # Si plan_id est vide, c'est le plan Free
                    data['plan_name'] = 'B2B Free'
                    data['monthly_fee'] = 0
                    data['plan'] = None
                
                # Supprimer plan_id car le serializer n'attend que 'plan'
                if 'plan_id' in data:
                    del data['plan_id']
            
            serializer = B2BStoreSubscriptionSerializer(subscription, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                # Recharger l'objet depuis la DB pour avoir toutes les données à jour
                subscription.refresh_from_db()
                # Réutiliser le serializer avec l'objet rafraîchi pour avoir tous les champs calculés
                updated_serializer = B2BStoreSubscriptionSerializer(subscription)
                return Response({
                    'success': True,
                    'data': updated_serializer.data
                })
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except B2BStoreSubscription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Abonnement introuvable'
            }, status=status.HTTP_404_NOT_FOUND)

