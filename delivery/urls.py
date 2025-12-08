from django.urls import path
from .views import DeliveryAgentListView, DeliveryAgentDetailView, DeliveryStatsView

urlpatterns = [
    path('agents/', DeliveryAgentListView.as_view(), name='delivery-agents-list'),
    path('agents/<int:pk>/', DeliveryAgentDetailView.as_view(), name='delivery-agent-detail'),
    path('stats/', DeliveryStatsView.as_view(), name='delivery-stats'),
]
