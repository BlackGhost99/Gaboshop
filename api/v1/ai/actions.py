"""
Préparation et confirmation d'actions IA
"""
import os
import json
import time
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
from django.utils import timezone
from products.models import Product
from orders.models import Order, OrderItem
from stores.models import Store
from .permissions import AIPermissionChecker
from .providers import AIProvider
from api.models import AIActionLog
from core.models import AuditLog


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def prepare_order(request):
    """
    POST /api/v1/ai/prepare-order
    
    Prépare une commande à partir d'une intention utilisateur
    Ne modifie RIEN en base de données
    
    Body:
    {
        "intent": "commander 2 sacs de riz",
        "store_id": 12  // optionnel
    }
    """
    user = request.user
    if user.user_type != 'client':
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_403_FORBIDDEN,
                "message": "Seuls les clients peuvent préparer des commandes."
            }
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Vérifier permissions
    allowed, reason = AIPermissionChecker.can_execute_action('prepare_order', user)
    if not allowed:
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_403_FORBIDDEN,
                "message": reason
            }
        }, status=status.HTTP_403_FORBIDDEN)
    
    intent = request.data.get('intent', '').strip()
    store_id = request.data.get('store_id')
    
    if not intent:
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "Le paramètre 'intent' est requis."
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Vérifier si un provider IA est disponible
    provider_config = AIProvider.get_provider_config()
    
    # Cette fonctionnalité nécessite un LLM pour interpréter les intentions naturelles
    if not provider_config['available'] or provider_config['name'] == 'local':
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_503_SERVICE_UNAVAILABLE,
                "message": f"La préparation de commande par IA nécessite un service d'IA configuré.\n\nOptions gratuites:\n- DeepSeek (1M tokens/mois GRATUIT): Configurez DEEPSEEK_API_KEY\n- Anthropic Claude: Configurez ANTHROPIC_API_KEY\n- OpenAI: Configurez OPENAI_API_KEY\n\nPour activer, définissez AI_PROVIDER dans settings.py (deepseek, anthropic, ou openai) et la clé correspondante.\n\nEn attendant, vous pouvez créer des commandes manuellement depuis la page des produits."
            }
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    try:
        
        # Récupérer les produits disponibles
        products = Product.objects.filter(
            is_available=True,
            store__is_active=True,
            market_type__in=['b2c', 'both'],
            stock__gt=0
        )
        
        if store_id:
            products = products.filter(store_id=store_id)
        
        products_list = []
        for p in products[:50]:  # Limiter pour le prompt
            products_list.append({
                "id": p.id,
                "name": p.name,
                "price": float(p.price),
                "stock": p.stock,
                "store_id": p.store.id,
                "store_name": p.store.name,
            })
        
        interpretation_prompt = f"""Tu es un assistant qui prépare des commandes e-commerce.
L'utilisateur veut: "{intent}"

Produits disponibles:
{json.dumps(products_list, indent=2, ensure_ascii=False)}

Identifie les produits correspondants et prépare une commande.
Retourne UNIQUEMENT un JSON:
{{
    "items": [
        {{"product_id": id, "quantity": nombre, "unit_price": prix}}
    ],
    "store_id": id_du_magasin,
    "notes": "notes optionnelles"
}}

Si plusieurs magasins, choisis le premier disponible."""
        
        # Utiliser le provider configuré
        try:
            interpretation_text = AIProvider.call_ai(
                "Tu es un assistant qui prépare des commandes e-commerce. Retourne UNIQUEMENT du JSON valide.",
                interpretation_prompt,
                provider_config
            )
        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            error_trace = traceback.format_exc()
            logger.error(f"Erreur lors de l'appel au provider IA ({provider_config['name']}): {str(e)}\n{error_trace}")
            
            # Message d'erreur plus détaillé pour le débogage
            error_str = str(e)
            error_message = f"Erreur de communication avec le service IA ({provider_config['name']}): {error_str}"
            
            if "Insufficient Balance" in error_str or "402" in error_str:
                error_message = f"Le compte {provider_config['name']} n'a pas assez de crédits.\n\nVeuillez recharger votre compte sur https://platform.deepseek.com/ ou utiliser un autre provider IA."
            elif "401" in error_str or "unauthorized" in error_str.lower():
                error_message += "\n\nLa clé API semble invalide. Vérifiez DEEPSEEK_API_KEY dans settings.py"
            elif "404" in error_str or "not found" in error_str.lower():
                error_message += "\n\nL'URL de l'API semble incorrecte. Vérifiez la configuration."
            elif "rate limit" in error_str.lower() or "429" in error_str:
                error_message += "\n\nLimite de requêtes atteinte. Réessayez plus tard."
            
            return Response({
                "success": False,
                "error": {
                    "code": status.HTTP_503_SERVICE_UNAVAILABLE,
                    "message": error_message
                }
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        if not interpretation_text:
            return Response({
                "success": False,
                "error": {
                    "code": status.HTTP_503_SERVICE_UNAVAILABLE,
                    "message": f"Le service IA ({provider_config['name']}) n'a pas retourné de réponse. Vérifiez votre configuration API ou réessayez plus tard."
                }
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        # Parser le JSON (gérer différents formats de réponse)
        import re
        order_data = None
        
        # Chercher JSON entre ```json et ``` ou directement
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', interpretation_text, re.DOTALL)
        if json_match and json_match.groups():
            try:
                order_data = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Si pas trouvé, chercher un JSON simple
        if not order_data:
            json_match = re.search(r'\{.*\}', interpretation_text, re.DOTALL)
            if json_match:
                try:
                    order_data = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        if not order_data:
            return Response({
                "success": False,
                "error": {
                    "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": f"Impossible d'interpréter l'intention. Réponse IA invalide.\n\nRéponse reçue: {interpretation_text[:200]}"
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Valider et calculer
        items = order_data.get('items', [])
        store_id = order_data.get('store_id')
        
        if not items or not store_id:
            return Response({
                "success": False,
                "error": {
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Impossible de préparer la commande. Produits introuvables ou magasin invalide."
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                "success": False,
                "error": {
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Magasin introuvable."
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Calculer le total
        items_total = 0
        order_items = []
        
        for item in items:
            product_id = item.get('product_id')
            quantity = item.get('quantity', 1)
            
            try:
                product = Product.objects.get(
                    id=product_id,
                    store=store,
                    is_available=True,
                    stock__gte=quantity
                )
                unit_price = float(product.price)
                subtotal = unit_price * quantity
                items_total += subtotal
                
                order_items.append({
                    "product": {
                        "id": product.id,
                        "name": product.name,
                    },
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                })
            except Product.DoesNotExist:
                continue
        
        if not order_items:
            return Response({
                "success": False,
                "error": {
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Aucun produit valide trouvé pour cette commande."
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculer frais
        from decimal import Decimal
        delivery_fee = float(store.delivery_fee) if store.delivery_fee else 0.0
        service_fee = float(store.service_fee) if store.service_fee else 0.0
        total = items_total + delivery_fee + service_fee
        
        # Créer un résumé
        summary_items = ", ".join([f"{item['quantity']}x {item['product']['name']}" for item in order_items[:3]])
        if len(order_items) > 3:
            summary_items += f" et {len(order_items) - 3} autre(s)"
        
        summary = f"{summary_items} – {items_total:,.0f} FCFA"
        
        # Log l'action (non confirmée)
        AIActionLog.objects.create(
            initiator=user,
            action='prepare_order',
            details={
                "intent": intent,
                "store_id": store_id,
                "items_count": len(order_items),
                "total": total,
            },
            confirmed=False,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        
        return Response({
            "success": True,
            "data": {
                "summary": summary,
                "items": order_items,
                "totals": {
                    "items_total": items_total,
                    "delivery_fee": delivery_fee,
                    "service_fee": service_fee,
                    "total": total,
                },
                "store": {
                    "id": store.id,
                    "name": store.name,
                },
                "requires_confirmation": True,
                "preparation_id": f"prep_{user.id}_{int(timezone.now().timestamp())}",
            }
        })
    
    except Exception as e:
        import traceback
        error_details = str(e)
        traceback_str = traceback.format_exc()
        
        # Logger l'erreur pour le débogage
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Erreur dans prepare_order: {error_details}\n{traceback_str}")
        
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Erreur lors de la préparation: {error_details}"
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def confirm_action(request):
    """
    POST /api/v1/ai/confirm-action
    
    Confirme et exécute une action préparée par l'IA
    
    Body:
    {
        "action_type": "order",
        "preparation_data": {...}  // données de prepare-order
    }
    """
    user = request.user
    action_type = request.data.get('action_type')
    preparation_data = request.data.get('preparation_data', {})
    
    if not action_type:
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "Le paramètre 'action_type' est requis."
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if action_type == 'order':
        # Vérifier permissions
        allowed, reason = AIPermissionChecker.can_execute_action('prepare_order', user)
        if not allowed:
            return Response({
                "success": False,
                "error": {
                    "code": status.HTTP_403_FORBIDDEN,
                    "message": reason
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Récupérer les données de préparation
        items = preparation_data.get('items', [])
        store_id = preparation_data.get('store', {}).get('id')
        totals = preparation_data.get('totals', {})
        
        if not items or not store_id:
            return Response({
                "success": False,
                "error": {
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": "Données de préparation invalides."
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            store = Store.objects.get(id=store_id, is_active=True)
        except Store.DoesNotExist:
            return Response({
                "success": False,
                "error": {
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": "Magasin introuvable."
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Créer la commande
        from decimal import Decimal
        
        order = Order.objects.create(
            client=user,
            store=store,
            items_total=Decimal(str(totals.get('items_total', 0))),
            delivery_fee=Decimal(str(totals.get('delivery_fee', 0))),
            service_fee=Decimal(str(totals.get('service_fee', 0))),
            total_amount=Decimal(str(totals.get('total', 0))),
            status='created',
            delivery_address=request.data.get('delivery_address', ''),
            delivery_phone=user.phone,
            delivery_zone=request.data.get('delivery_zone', ''),
        )
        
        # Créer les OrderItems
        for item in items:
            product_id = item.get('product', {}).get('id')
            quantity = item.get('quantity', 1)
            
            try:
                product = Product.objects.get(id=product_id)
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    unit_price=Decimal(str(item.get('unit_price', 0))),
                )
            except Product.DoesNotExist:
                continue
        
        # Log l'action confirmée
        action_log = AIActionLog.objects.create(
            initiator=user,
            action='confirm_order',
            details={
                "order_id": order.id,
                "order_number": order.order_number,
                "total": float(order.total_amount),
            },
            confirmed=True,
            success=True,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
        )
        
        # Log dans AuditLog
        AuditLog.log_action(
            action_type='order_created',
            user=user,
            object_type='order',
            object_id=order.id,
            old_value=None,
            new_value='created',
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            reason=f'Commande créée via IA (action_log_id: {action_log.id})'
        )
        
        return Response({
            "success": True,
            "data": {
                "order": {
                    "id": order.id,
                    "order_number": order.order_number,
                    "total": float(order.total_amount),
                    "status": order.status,
                },
                "message": "Commande créée avec succès."
            }
        })
    
    else:
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_400_BAD_REQUEST,
                "message": f"Type d'action non supporté: {action_type}"
            }
        }, status=status.HTTP_400_BAD_REQUEST)

