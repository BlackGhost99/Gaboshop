"""
AI Gateway - Endpoint principal pour communiquer avec Claude API
"""
import os
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
from .services import AIContextService, AIGatewayService, ErrorAnalyzer
from .local_ai import LocalAI
from .providers import AIProvider


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def ai_chat(request):
    """
    POST /api/v1/ai/chat
    
    Reçoit un message utilisateur et retourne une réponse de l'IA
    
    Body:
    {
        "message": "string",
        "frontend_context": {
            "page": "orders_b2b",
            "route": "/orders-b2b",
            "last_api_error": {...}
        }
    }
    """
    try:
        user = request.user
        message = request.data.get('message', '').strip()
        frontend_context = request.data.get('frontend_context', {})
        last_error = frontend_context.get('last_api_error')
        
        if not message:
            return Response({
                "success": False,
                "error": {
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Le message ne peut pas être vide."
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Construire le contexte complet
        full_context = AIContextService.get_full_context(user, frontend_context)
        
        # Construire les prompts
        system_prompt = AIGatewayService.build_system_prompt(full_context)
        user_message = AIGatewayService.build_user_message(message, full_context, last_error)
        
        # Obtenir la configuration du provider
        provider_config = AIProvider.get_provider_config()
        
        # Essayer d'appeler le provider d'IA
        ai_response = None
        if provider_config['available']:
            ai_response = AIProvider.call_ai(system_prompt, user_message, provider_config)
        
        # Fallback vers mode local si le provider n'a pas fonctionné
        if not ai_response:
            ai_response = LocalAI.generate_response(message, full_context, last_error)
            provider_config['name'] = 'local'
        
        return Response({
            "success": True,
            "data": {
                "message": ai_response,
                "context_used": {
                    "role": user.user_type,
                    "has_store": "store" in full_context,
                    "has_alerts": len(full_context.get("alerts", [])) > 0,
                    "provider": provider_config['name'],
                }
            }
        })
    
    except Exception as e:
        # Si erreur avec le provider, fallback vers local
        try:
            if 'provider_config' in locals() and provider_config.get('name') != 'local':
                full_context = AIContextService.get_full_context(user, frontend_context)
                ai_response = LocalAI.generate_response(message, full_context, last_error)
                
                return Response({
                    "success": True,
                    "data": {
                        "message": ai_response + f"\n\n(Note: Erreur avec le provider. Mode local activé.)",
                        "context_used": {
                            "role": user.user_type,
                            "has_store": "store" in full_context,
                            "has_alerts": len(full_context.get("alerts", [])) > 0,
                            "provider": "local",
                        }
                    }
                })
            else:
                # Fallback local direct
                full_context = AIContextService.get_full_context(user, frontend_context)
                ai_response = LocalAI.generate_response(message, full_context, last_error)
                
                return Response({
                    "success": True,
                    "data": {
                        "message": ai_response,
                        "context_used": {
                            "role": user.user_type,
                            "has_store": "store" in full_context,
                            "has_alerts": len(full_context.get("alerts", [])) > 0,
                            "provider": "local",
                        }
                    }
                })
        except Exception as fallback_error:
            return Response({
                "success": False,
                "error": {
                    "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": f"Erreur interne: {str(e)}"
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

