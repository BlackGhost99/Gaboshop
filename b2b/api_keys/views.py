"""Accès API des grossistes : gestion des clés (session normale) et endpoints d'intégration (clé API).

Les endpoints d'intégration lisent les produits et les commandes reçues du grossiste propriétaire de la clé, et ne
modifient que le stock et le prix des produits. Aucune action sur l'argent (paiement, remboursement, versement)
n'existe ici.
"""
from django.db import transaction
from django.db.models import Prefetch
from rest_framework import exceptions, permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from b2b.api_keys.authentication import (
    ApiKeyAuthentication, ApiKeyRateThrottle, HasWholesalerApiKey,
)
from b2b.api_keys.serializers import (
    ApiKeyCreateSerializer, ApiKeySerializer, IntegrationOrderDetailSerializer, IntegrationOrderSerializer,
    IntegrationProductSerializer, IntegrationProductUpdateSerializer,
)
from b2b.models import B2BProductPricing, WholesalerApiKey
from b2b.models.api_key import MAX_ACTIVE_KEYS
from orders.models import Order
from payments.plan_features import PlanFeatureRequired, has, plan_for_sale, require, required_message
from products.models import Product
from stores.models import Store

INTEGRATION_PATH = '/api/v1/b2b/integration/'


def _error(message, code, http_status):
    return Response({'success': False, 'error': {'code': code, 'message': message}}, status=http_status)


def _wholesaler(request):
    """(grossiste, réponse d'erreur) : l'accès API est réservé aux grossistes."""
    store = Store.objects.filter(manager=request.user, is_active=True).first()
    if store is None:
        return None, _error("Aucune boutique active n'est liée à votre compte.", 'no_store', status.HTTP_403_FORBIDDEN)
    if not store.is_b2b:
        return None, _error("L'accès API est réservé aux grossistes.", 'wholesaler_only', status.HTTP_403_FORBIDDEN)
    return store, None


# ==================== Gestion des clés (session normale du grossiste) ====================

class ApiKeyListCreateView(APIView):
    """GET /b2b/api-keys/ : l'état de l'option et les clés. POST : crée une clé (montrée une seule fois)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        store, error = _wholesaler(request)
        if error:
            return error
        plan = store.get_current_plan()
        enabled = has(plan, 'api_access')
        target = None if enabled else plan_for_sale(plan, lambda candidate: has(candidate, 'api_access'))
        keys = store.api_keys.all()
        return Response({'success': True, 'data': {
            'enabled': enabled,
            'plan_name': getattr(plan, 'name', ''),
            'message': '' if enabled else required_message('api_access', plan),
            'required_plan': {'name': target.name, 'price': str(target.price)} if target else None,
            'max_active_keys': MAX_ACTIVE_KEYS,
            'active_count': sum(1 for key in keys if key.is_active),
            'base_path': INTEGRATION_PATH,
            'keys': ApiKeySerializer(keys, many=True).data,
        }})

    def post(self, request):
        store, error = _wholesaler(request)
        if error:
            return error
        try:
            require(store, 'api_access')
        except PlanFeatureRequired as exc:
            return _error(str(exc), 'plan_required', status.HTTP_403_FORBIDDEN)
        serializer = ApiKeyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({'success': False, 'error': {
                'code': status.HTTP_400_BAD_REQUEST, 'message': 'Données invalides.', 'details': serializer.errors,
            }}, status=status.HTTP_400_BAD_REQUEST)
        with transaction.atomic():
            Store.objects.select_for_update().get(pk=store.pk)  # deux créations simultanées ne dépassent pas la limite
            if store.api_keys.filter(is_active=True).count() >= MAX_ACTIVE_KEYS:
                return _error(f"Vous avez déjà {MAX_ACTIVE_KEYS} clés actives. Révoquez-en une avant d'en créer une nouvelle.",
                              'too_many_keys', status.HTTP_400_BAD_REQUEST)
            key, raw = WholesalerApiKey.generate(store, serializer.validated_data['name'])
        return Response({
            'success': True,
            'message': 'Clé créée. Copiez-la maintenant : elle ne sera plus jamais affichée.',
            'data': {
                'key': ApiKeySerializer(key).data,
                'api_key': raw,
                'warning': "Cette clé donne accès à votre stock et à vos commandes. Gardez-la secrète ; "
                           "en cas de doute, révoquez-la et créez-en une autre.",
            },
        }, status=status.HTTP_201_CREATED)


class ApiKeyRevokeView(APIView):
    """POST /b2b/api-keys/<id>/revoke/ : coupe la clé tout de suite (possible même sans l'option dans le forfait)."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, key_id):
        store, error = _wholesaler(request)
        if error:
            return error
        key = store.api_keys.filter(pk=key_id).first()
        if key is None:
            return _error("Cette clé n'existe pas.", 'not_found', status.HTTP_404_NOT_FOUND)
        already = not key.is_active
        key.revoke()
        return Response({
            'success': True,
            'message': 'Cette clé était déjà révoquée.' if already else
                       f"La clé « {key.name} » est révoquée : les logiciels qui l'utilisent n'ont plus accès.",
            'data': ApiKeySerializer(key).data,
        })


# ==================== Intégration (authentifiée par clé) ====================

class IntegrationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    invalid_page_message = 'Page invalide.'


class IntegrationView(APIView):
    authentication_classes = [ApiKeyAuthentication]
    permission_classes = [HasWholesalerApiKey]
    throttle_classes = [ApiKeyRateThrottle]

    @property
    def store(self):
        return self.request.auth.store

    def throttled(self, request, wait):
        seconds = int(wait or 1) + 1
        raise exceptions.Throttled(wait, detail=(
            f"Trop de requêtes : 60 par minute et par clé au maximum. Réessayez dans {seconds} seconde"
            f"{'s' if seconds > 1 else ''}."))

    def paginate(self, queryset, serializer_class):
        paginator = IntegrationPagination()
        page = paginator.paginate_queryset(queryset, self.request, view=self)
        return paginator.get_paginated_response(serializer_class(page, many=True).data)


def _truthy(value):
    return str(value).strip().lower() in ('1', 'true', 'oui', 'yes')


class IntegrationProductListView(IntegrationView):
    """GET /b2b/integration/products/?search=&is_available=true|false&page=&page_size="""

    def get(self, request):
        products = Product.objects.filter(store=self.store).prefetch_related(
            Prefetch('b2b_pricings', queryset=B2BProductPricing.objects.filter(is_active=True).order_by('min_quantity'))
        ).order_by('id')
        search = request.query_params.get('search', '').strip()
        if search:
            products = products.filter(name__icontains=search)
        available = request.query_params.get('is_available')
        if available not in (None, ''):
            products = products.filter(is_available=_truthy(available))
        return self.paginate(products, IntegrationProductSerializer)


class IntegrationProductDetailView(IntegrationView):
    """GET / PATCH /b2b/integration/products/<id>/ : PATCH ne change que stock et price."""

    def _product(self, product_id):
        product = Product.objects.filter(store=self.store, pk=product_id).first()
        if product is None:
            raise exceptions.NotFound("Ce produit n'existe pas dans votre boutique.")
        return product

    def get(self, request, product_id):
        return Response(IntegrationProductSerializer(self._product(product_id)).data)

    def patch(self, request, product_id):
        product = self._product(product_id)
        data = request.data
        if not hasattr(data, 'keys'):
            raise exceptions.ValidationError({'detail': 'Envoyez un objet JSON, ex. {"stock": 12}.'})
        serializer = IntegrationProductUpdateSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=product.pk)
            for name, value in serializer.validated_data.items():
                setattr(product, name, value)
            product.save(update_fields=[*serializer.validated_data, 'updated_at'])
        return Response(IntegrationProductSerializer(product).data)


class IntegrationOrderListView(IntegrationView):
    """GET /b2b/integration/orders/?status=paid,confirmed&page=&page_size= : commandes reçues (lecture seule)."""

    def get_queryset(self):
        return (Order.objects.filter(store=self.store, is_b2b=True)
                .select_related('source_store').prefetch_related('items__product').order_by('-created_at', '-id'))

    def get(self, request):
        orders = self.get_queryset()
        raw = request.query_params.get('status', '').strip()
        if raw:
            wanted = [part.strip() for part in raw.split(',') if part.strip()]
            valid = [code for code, _ in Order.ORDER_STATUS_CHOICES]
            unknown = [code for code in wanted if code not in valid]
            if unknown:
                raise exceptions.ValidationError({'status': f"Statut inconnu : {', '.join(unknown)}. "
                                                            f"Valeurs possibles : {', '.join(valid)}."})
            orders = orders.filter(status__in=wanted)
        return self.paginate(orders, IntegrationOrderSerializer)


class IntegrationOrderDetailView(IntegrationOrderListView):
    """GET /b2b/integration/orders/<id>/ : détail d'une commande reçue."""

    def get(self, request, order_id):
        order = self.get_queryset().filter(pk=order_id).first()
        if order is None:
            raise exceptions.NotFound("Cette commande n'existe pas parmi vos commandes reçues.")
        return Response(IntegrationOrderDetailSerializer(order).data)
