"""
Recherche intelligente de produits avec interprétation IA
"""
import os
import json
import re
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.conf import settings
from django.db.models import Q
from products.models import Product
from .permissions import AIPermissionChecker
from .providers import AIProvider


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def ai_search_products(request):
    """
    GET /api/v1/ai/search/products?query=riz alimentaire moins de 2000 FCFA
    
    Recherche intelligente de produits avec interprétation naturelle
    """
    # Vérifier permissions
    user = request.user
    store = None
    if user.user_type == 'store_manager':
        store = user.managed_stores.filter(is_active=True).first()
    
    allowed, reason = AIPermissionChecker.can_execute_action('search_products', user, store)
    if not allowed:
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_403_FORBIDDEN,
                "message": reason
            }
        }, status=status.HTTP_403_FORBIDDEN)
    
    query = request.query_params.get('query', '').strip()
    if not query:
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_400_BAD_REQUEST,
                "message": "Le paramètre 'query' est requis."
            }
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Obtenir la configuration du provider
        provider_config = AIProvider.get_provider_config()
        
        # Mode local : recherche simple sans interprétation IA
        if not provider_config['available'] or provider_config['name'] == 'local':
            # Recherche simple par mots-clés
            queryset = Product.objects.filter(
                is_available=True,
                store__is_active=True,
                market_type__in=['b2c', 'both']
            ).select_related('store', 'category')
            
            # Recherche simple par nom/description
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query)
            )[:20]
            
            products_data = []
            for product in queryset:
                products_data.append({
                    "id": product.id,
                    "name": product.name,
                    "price": float(product.price),
                    "stock": product.stock,
                    "store": {
                        "id": product.store.id,
                        "name": product.store.name,
                    },
                    "category": product.category.name if product.category else None,
                })
            
            return Response({
                "success": True,
                "data": {
                    "query": query,
                    "interpretation": {"search_text": query, "mode": "simple"},
                    "summary": f"J'ai trouvé {len(products_data)} produit(s) correspondant à '{query}'. (Mode recherche simple - configurez un provider IA pour une recherche intelligente)",
                    "products": products_data,
                    "count": len(products_data),
                }
            })
        
        # Utiliser le provider IA pour interpréter la requête
        interpretation_prompt = f"""Tu es un assistant qui interprète des requêtes de recherche de produits.
Analyse cette requête et extrais les critères de recherche:
"{query}"

Retourne UNIQUEMENT un JSON avec ces champs (null si non spécifié):
{{
    "search_text": "texte à rechercher dans nom/description",
    "category": "catégorie si mentionnée",
    "max_price": nombre ou null,
    "min_price": nombre ou null,
    "in_stock": true/false/null,
    "store_id": nombre ou null
}}

Exemple pour "riz alimentaire moins de 2000 FCFA":
{{
    "search_text": "riz",
    "category": "alimentaire",
    "max_price": 2000,
    "min_price": null,
    "in_stock": true,
    "store_id": null
}}"""
        
        interpretation_text = AIProvider.call_ai(
            "Tu es un assistant qui interprète des requêtes de recherche. Retourne UNIQUEMENT du JSON valide.",
            interpretation_prompt,
            provider_config
        )
        
        if not interpretation_text:
            # Fallback vers recherche simple
            interpretation_text = f'{{"search_text": "{query}"}}'
        
        # Parser le JSON
        json_match = re.search(r'\{[^}]+\}', interpretation_text, re.DOTALL)
        if json_match:
            criteria = json.loads(json_match.group())
        else:
            # Fallback: recherche simple
            criteria = {"search_text": query}
        
        # Construire la requête Django
        queryset = Product.objects.filter(
            is_available=True,
            store__is_active=True,
            market_type__in=['b2c', 'both']
        ).select_related('store', 'category')
        
        # Appliquer les filtres
        if criteria.get('search_text'):
            queryset = queryset.filter(
                Q(name__icontains=criteria['search_text']) |
                Q(description__icontains=criteria['search_text'])
            )
        
        if criteria.get('category'):
            queryset = queryset.filter(
                Q(category__name__icontains=criteria['category']) |
                Q(store__category__name__icontains=criteria['category'])
            )
        
        if criteria.get('max_price'):
            queryset = queryset.filter(price__lte=criteria['max_price'])
        
        if criteria.get('min_price'):
            queryset = queryset.filter(price__gte=criteria['min_price'])
        
        if criteria.get('in_stock') is True:
            queryset = queryset.filter(stock__gt=0)
        
        if criteria.get('store_id'):
            queryset = queryset.filter(store_id=criteria['store_id'])
        
        # Limiter à 20 résultats
        products = queryset[:20]
        
        # Formater les résultats
        products_data = []
        for product in products:
            products_data.append({
                "id": product.id,
                "name": product.name,
                "price": float(product.price),
                "stock": product.stock,
                "store": {
                    "id": product.store.id,
                    "name": product.store.name,
                },
                "category": product.category.name if product.category else None,
            })
        
        # Reformuler les résultats avec le provider IA
        reformulation_prompt = f"""Tu as trouvé {len(products_data)} produit(s) pour la requête "{query}".

Résume les résultats de manière naturelle et utile en français.
Mentionne les prix, disponibilités, et magasins si pertinent.
Sois concis (2-3 phrases max)."""
        
        if products_data:
            reformulation_prompt += f"\n\nProduits trouvés:\n{json.dumps(products_data[:5], indent=2, ensure_ascii=False)}"
        
        summary = AIProvider.call_ai(
            "Tu es un assistant qui résume des résultats de recherche de produits en français.",
            reformulation_prompt,
            provider_config
        )
        
        if not summary:
            # Fallback vers résumé simple
            summary = f"J'ai trouvé {len(products_data)} produit(s) correspondant à '{query}'."
        
        return Response({
            "success": True,
            "data": {
                "query": query,
                "interpretation": criteria,
                "summary": summary,
                "products": products_data,
                "count": len(products_data),
                "provider": provider_config['name'],
            }
        })
    
    except Exception as e:
        return Response({
            "success": False,
            "error": {
                "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "message": f"Erreur lors de la recherche: {str(e)}"
            }
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
