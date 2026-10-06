"""
URLs pour le module AI
"""
from django.urls import path
from .context import get_ai_context
from .gateway import ai_chat
from .search import ai_search_products
from .actions import prepare_order
from .logs import get_ai_logs
from .shopping import ai_shop
from .assistant import ai_assistant, ai_assistant_confirm, ai_assistant_status

app_name = 'ai'

urlpatterns = [
    path('context/', get_ai_context, name='ai-context'),
    path('chat/', ai_chat, name='ai-chat'),
    path('shop/', ai_shop, name='ai-shop'),
    path('assistant/', ai_assistant, name='ai-assistant'),
    path('assistant/confirm/', ai_assistant_confirm, name='ai-assistant-confirm'),
    path('assistant/status/', ai_assistant_status, name='ai-assistant-status'),
    path('search/products/', ai_search_products, name='ai-search-products'),
    path('prepare-order/', prepare_order, name='ai-prepare-order'),
    # L'ancien « confirm-action » est retiré : il prenait les prix envoyés par le client.
    # Les actions de l'assistant passent par assistant/confirm/ (jeton signé, contrôles serveur).
    path('logs/', get_ai_logs, name='ai-logs'),
]

