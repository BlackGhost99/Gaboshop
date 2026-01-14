"""
URLs pour le module AI
"""
from django.urls import path
from .context import get_ai_context
from .gateway import ai_chat
from .search import ai_search_products
from .actions import prepare_order, confirm_action
from .logs import get_ai_logs

app_name = 'ai'

urlpatterns = [
    path('context/', get_ai_context, name='ai-context'),
    path('chat/', ai_chat, name='ai-chat'),
    path('search/products/', ai_search_products, name='ai-search-products'),
    path('prepare-order/', prepare_order, name='ai-prepare-order'),
    path('confirm-action/', confirm_action, name='ai-confirm-action'),
    path('logs/', get_ai_logs, name='ai-logs'),
]

