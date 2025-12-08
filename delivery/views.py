from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count, Avg, Q
from users.models import User
from .models import Delivery, DeliveryProfile
from .serializers import DeliveryAgentSerializer, DeliverySerializer

class IsPlatformAdmin(permissions.BasePermission):
    """Allow staff or explicit user_type 'admin' to manage delivery agents."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or getattr(user, 'user_type', '') == 'admin'))


class DeliveryAgentListView(generics.ListCreateAPIView):
    serializer_class = DeliveryAgentSerializer
    permission_classes = [IsPlatformAdmin]
    
    def get_queryset(self):
        return User.objects.filter(user_type='delivery_agent').select_related('delivery_profile')

class DeliveryAgentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DeliveryAgentSerializer
    permission_classes = [IsPlatformAdmin]
    
    def get_queryset(self):
        return User.objects.filter(user_type='delivery_agent').select_related('delivery_profile')

class DeliveryStatsView(APIView):
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        total_deliveries = Delivery.objects.count()
        active_deliveries = Delivery.objects.filter(status__in=['assigned', 'accepted', 'picked_up', 'in_transit']).count()
        completed_deliveries = Delivery.objects.filter(status='delivered').count()
        
        # Agent stats
        total_agents = User.objects.filter(user_type='delivery_agent').count()
        active_agents = DeliveryProfile.objects.filter(status='available').count()
        
        return Response({
            'total_deliveries': total_deliveries,
            'active_deliveries': active_deliveries,
            'completed_deliveries': completed_deliveries,
            'total_agents': total_agents,
            'active_agents': active_agents
        })
