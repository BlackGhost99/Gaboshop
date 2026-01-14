"""
Endpoint pour consulter les logs d'actions IA (admin seulement)
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from api.models import AIActionLog
from django.utils import timezone
from datetime import timedelta


class IsAdmin(permissions.BasePermission):
    """Permission pour les administrateurs seulement"""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


@api_view(['GET'])
@permission_classes([IsAdmin])
def get_ai_logs(request):
    """
    GET /api/v1/ai/logs
    
    Liste toutes les actions IA avec filtres
    Query params:
    - action: filtrer par type d'action
    - confirmed: true/false
    - user_id: filtrer par utilisateur
    - days: nombre de jours (défaut: 7)
    """
    try:
        queryset = AIActionLog.objects.all().select_related('initiator')
        
        # Filtres
        action_filter = request.query_params.get('action')
        if action_filter:
            queryset = queryset.filter(action=action_filter)
        
        confirmed_filter = request.query_params.get('confirmed')
        if confirmed_filter is not None:
            confirmed = confirmed_filter.lower() == 'true'
            queryset = queryset.filter(confirmed=confirmed)
        
        user_id = request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(initiator_id=user_id)
        
        days = int(request.query_params.get('days', 7))
        since = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(timestamp__gte=since)
        
        # Pagination simple
        limit = int(request.query_params.get('limit', 50))
        offset = int(request.query_params.get('offset', 0))
        
        total = queryset.count()
        logs = queryset.order_by('-timestamp')[offset:offset + limit]
        
        logs_data = []
        for log in logs:
            logs_data.append({
                "id": log.id,
                "actor": log.actor,
                "initiator": {
                    "id": log.initiator.id if log.initiator else None,
                    "phone": log.initiator.phone if log.initiator else None,
                    "role": log.initiator.user_type if log.initiator else None,
                },
                "action": log.action,
                "details": log.details,
                "confirmed": log.confirmed,
                "success": log.success,
                "error_message": log.error_message,
                "timestamp": log.timestamp.isoformat(),
                "ip_address": str(log.ip_address) if log.ip_address else None,
            })
        
        return Response({
            "success": True,
            "data": {
                "logs": logs_data,
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        })
    
    except Exception as e:
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": str(e)
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

