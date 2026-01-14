"""
API endpoint pour récupérer le contexte IA
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from .services import AIContextService
from .alerts import AlertMonitor


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_ai_context(request):
    """
    GET /api/v1/ai/context
    
    Retourne le contexte complet pour l'IA:
    - Informations utilisateur
    - Informations magasin (si store_manager)
    - Abonnements
    - Alertes
    - Métriques
    """
    try:
        user = request.user
        context = AIContextService.get_user_context(user)
        
        # Ajouter les alertes
        store = None
        if user.user_type == 'store_manager':
            store = user.managed_stores.filter(is_active=True).first()
        
        alerts = AlertMonitor.get_all_alerts(store=store, user_role=user.user_type)
        context["alerts"] = [alert.get("type") for alert in alerts]
        context["alerts_details"] = alerts
        
        # Métriques préventives
        if "metrics" not in context:
            context["metrics"] = {}
        
        # Ajouter métriques de stock critique
        if store:
            from products.models import Product
            critical_stock = Product.objects.filter(
                store=store,
                is_available=True,
                stock__gt=0,
                stock__lte=10
            ).count()
            context["metrics"]["stock_critical"] = critical_stock > 0
            context["metrics"]["critical_stock_count"] = critical_stock
        
        return Response({
            "success": True,
            "data": context
        })
    
    except Exception as e:
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": str(e)
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

