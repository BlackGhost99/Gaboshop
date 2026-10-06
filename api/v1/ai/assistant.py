"""
Assistant IA Gaboshop : un agent qui utilise l'application à la place de l'utilisateur.

Il s'adapte au rôle (visiteur, client, commerce, livreur, admin) et dispose
d'« outils » : chercher des produits, ajouter au panier, suivre une commande,
voir le stock d'un commerce, les livraisons d'un livreur, les chiffres de l'admin…

- Avec une clé gratuite Groq (GROQ_API_KEY), le modèle choisit lui-même les outils
  (appel de fonctions) et répond naturellement.
- Sans clé, ou si Groq échoue, un moteur local répond avec les mêmes outils.

Les modifications côté serveur (prix, stock d'un produit) ne sont jamais faites
directement : l'assistant propose l'action, l'utilisateur la confirme d'un bouton
(jeton signé, revérifié à la confirmation). Les actions côté appareil (panier,
ouverture d'une page) sont renvoyées à l'application qui les exécute.
"""
import hashlib
import json
import logging
import re
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core import signing
from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response

from products.models import Product
from .shopping import (
    FAQ, ShopAnonThrottle, ShopUserThrottle, _plain, _price, extract_criteria,
    faq_answer, product_payload, search_catalog,
)

logger = logging.getLogger(__name__)

MAX_STEPS = 5
STATUS_CACHE_KEY = 'ai_assistant_last_status'
CONFIRM_SALT = 'gaboshop.ai.confirm'
CONFIRM_MAX_AGE = 15 * 60

ROLE_LABELS = {
    'visitor': 'visiteur non connecté',
    'client': 'client',
    'store_manager': 'gérant de commerce',
    'delivery_agent': 'livreur',
    'admin': 'administrateur de la plateforme',
}

ORDER_STATUS_FR = {
    'created': 'créée', 'pending_payment': 'en attente de paiement', 'paid': 'payée',
    'confirmed': 'confirmée', 'preparing': 'en préparation', 'ready': 'prête',
    'assigned': 'livreur assigné', 'in_transit': 'en livraison', 'delivered': 'livrée',
    'cancelled': 'annulée', 'refunded': 'remboursée',
}
ACTIVE_ORDER_STATUSES = ['created', 'pending_payment', 'paid', 'confirmed', 'preparing', 'ready', 'assigned', 'in_transit']
ACTIVE_DELIVERY_STATUSES = ['pending', 'assigned', 'accepted_by_driver', 'accepted', 'picked_up', 'in_delivery', 'in_transit']

PAGES = {
    'cart': '/client/dashboard',
    'orders': '/client/orders',
    'home': '/',
    'stores': '/boutiques',
    'login': '/login',
    'register': '/register',
    'store_dashboard': '/store/dashboard',
    'store_products': '/store/products',
    'store_orders': '/store/orders',
    'store_settings': '/store/settings/profile',
    'store_finance': '/store/finance',
    'delivery_dashboard': '/delivery/dashboard',
    'admin_dashboard': '/admin/dashboard',
}


def user_role(user):
    if not user or not user.is_authenticated:
        return 'visitor'
    if getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False):
        return 'admin'
    return user.user_type or 'client'


def _money(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _order_payload(o):
    return {
        'order_number': o.order_number,
        'status': ORDER_STATUS_FR.get(o.status, o.status),
        'total': _money(o.total_amount),
        'store': o.store.name if o.store_id else None,
        'date': o.created_at.strftime('%d/%m/%Y %H:%M') if o.created_at else None,
        'items': [f"{i.quantity} x {i.product.name}" for i in o.items.all()[:5]],
    }


class Ctx:
    """Ce que les outils accumulent pendant un tour : produits à afficher, actions, confirmations."""

    def __init__(self, request, role, cart):
        self.request = request
        self.user = request.user if request.user.is_authenticated else None
        self.role = role
        self.cart = cart
        self.products = {}
        self.actions = []
        self.confirmations = []

    def show(self, products):
        for p in products:
            self.products[p.id] = product_payload(p, self.request)

    def store(self):
        if self.user is None:
            return None
        return self.user.managed_stores.filter(is_active=True).first()


# ---------------------------------------------------------------------------
# Outils
# ---------------------------------------------------------------------------

def _blob(p):
    return _plain(' '.join([p.name, p.description or '', p.category.name if p.category_id else '',
                            ' '.join(str(v) for v in (p.attributes or {}).values())]))


def split_matches(found, keywords):
    """Sépare les produits qui contiennent tous les mots demandés de ceux qui n'en ont qu'une partie."""
    stems = [k[:-1] if len(k) > 4 and k[-1] in 'sx' else k for k in keywords]
    exact = [p for p in found if all(k in _blob(p) for k in stems)]
    return exact, [p for p in found if p not in exact]


def t_search_products(ctx, query='', max_price=None, min_price=None, brand=None, size=None, in_stock=None, store_id=None):
    criteria = extract_criteria(query or '')
    for key, value in (('max_price', max_price), ('min_price', min_price)):
        if value not in (None, ''):
            try:
                criteria[key] = float(value)
            except (TypeError, ValueError):
                pass
    criteria.update({'brand': brand, 'size': size, 'in_stock': in_stock, 'store_id': store_id})
    found = search_catalog(criteria, limit=8)
    if not found and brand and criteria['keywords']:
        found = search_catalog({**criteria, 'keywords': []}, limit=8)
    exact, partial = split_matches(found, criteria['keywords'])
    shown = exact or found
    ctx.show(shown)
    result = {'count': len(shown), 'products': [ctx.products[p.id] for p in shown]}
    if not exact and partial and len(criteria['keywords']) > 1:
        result['note'] = ("Aucun produit ne correspond à tous les mots ; ces produits n'en contiennent qu'une partie "
                          "(dis-le au client).")
    return result


def t_get_product(ctx, product_id):
    p = Product.objects.select_related('store', 'category').filter(
        id=product_id, is_available=True, store__is_active=True).first()
    if not p:
        return {'error': 'Produit introuvable ou indisponible.'}
    ctx.show([p])
    data = dict(ctx.products[p.id])
    data.update({
        'description': (p.description or '')[:500],
        'model': (p.attributes or {}).get('model'),
        'weight_kg': _money(p.weight_kg) if p.weight_kg else None,
    })
    return data


def t_add_to_cart(ctx, product_id, quantity=1, size=None):
    p = Product.objects.select_related('store').filter(
        id=product_id, is_available=True, store__is_active=True).first()
    if not p:
        return {'error': 'Produit introuvable ou indisponible.'}
    try:
        quantity = max(1, min(int(quantity or 1), 99))
    except (TypeError, ValueError):
        quantity = 1
    if p.stock is not None and p.stock <= 0:
        return {'error': f"{p.name} est en rupture de stock."}
    if p.stock and quantity > p.stock:
        return {'error': f"Il ne reste que {p.stock} {p.name} en stock."}
    ctx.show([p])
    item = ctx.products[p.id]
    if ctx.role == 'visitor':
        ctx.actions.append({'type': 'login_required', 'product': item, 'quantity': quantity})
        return {'ok': False, 'needs_login': True,
                'message': "Le client doit se connecter ou créer un compte pour ajouter au panier. "
                           "Le produit sera ajouté automatiquement après la connexion."}
    ctx.actions.append({'type': 'add_to_cart', 'product': item, 'quantity': quantity, 'size': size})
    return {'ok': True, 'added': f"{quantity} x {p.name}", 'unit_price': _money(p.price),
            'size': size, 'line_total': _money(p.price) * quantity}


def t_remove_from_cart(ctx, product_id):
    ctx.actions.append({'type': 'remove_from_cart', 'product_id': int(product_id)})
    return {'ok': True}


def t_view_cart(ctx):
    lines, total = [], 0.0
    for item in ctx.cart:
        qty = int(item.get('quantity') or 1)
        price = _money(item.get('price'))
        total += qty * price
        lines.append({'product_id': item.get('id'), 'name': item.get('name'), 'quantity': qty,
                      'unit_price': price, 'store': item.get('store_name')})
    return {'items': lines, 'items_total': total,
            'note': "Les frais de livraison s'ajoutent à la validation de la commande."}


def t_open_page(ctx, page, store_id=None, product_id=None):
    if page == 'store' and store_id:
        path = f"/stores/{int(store_id)}" + (f"?product={int(product_id)}" if product_id else '')
    elif page == 'product' and product_id:
        p = Product.objects.filter(id=product_id).only('store_id').first()
        if not p:
            return {'error': 'Produit introuvable.'}
        path = f"/stores/{p.store_id}?product={p.id}"
    else:
        path = PAGES.get(page)
    if not path:
        return {'error': f"Page inconnue : {page}"}
    ctx.actions.append({'type': 'navigate', 'path': path})
    return {'ok': True, 'path': path}


def t_my_orders(ctx, active_only=False):
    if ctx.user is None:
        return {'error': "Le client n'est pas connecté."}
    qs = ctx.user.orders.select_related('store').prefetch_related('items__product').order_by('-created_at')
    if active_only:
        qs = qs.filter(status__in=ACTIVE_ORDER_STATUSES)
    return {'orders': [_order_payload(o) for o in qs[:5]]}


def t_info(ctx, topic):
    answer = faq_answer(topic or '')
    return {'answer': answer or "\n".join(a for _, a in FAQ)}


def t_store_overview(ctx):
    store = ctx.store()
    if not store:
        return {'error': "Aucun commerce actif lié à ce compte."}
    since = timezone.now() - timedelta(days=7)
    orders = store.orders.all()
    week = orders.filter(created_at__gte=since).exclude(status__in=['cancelled', 'refunded'])
    products = store.products.all()
    low = products.filter(is_available=True, stock__lte=5).order_by('stock')[:8]
    return {
        'store': store.name,
        'orders_last_7_days': week.count(),
        'sales_last_7_days': _money(week.aggregate(s=Sum('items_total'))['s']),
        'orders_to_handle': orders.filter(status__in=['paid', 'confirmed', 'preparing']).count(),
        'products_total': products.count(),
        'products_visible': products.filter(is_available=True).count(),
        'low_stock': [{'product_id': p.id, 'name': p.name, 'stock': p.stock} for p in low],
        'has_logo': bool(store.logo), 'has_description': bool(store.description),
    }


def t_store_orders(ctx, status_filter='to_handle'):
    store = ctx.store()
    if not store:
        return {'error': "Aucun commerce actif lié à ce compte."}
    qs = store.orders.select_related('store').prefetch_related('items__product').order_by('-created_at')
    if status_filter == 'to_handle':
        qs = qs.filter(status__in=['paid', 'confirmed', 'preparing'])
    elif status_filter in ORDER_STATUS_FR:
        qs = qs.filter(status=status_filter)
    return {'orders': [_order_payload(o) for o in qs[:8]]}


def t_store_products(ctx, query='', low_stock_only=False):
    store = ctx.store()
    if not store:
        return {'error': "Aucun commerce actif lié à ce compte."}
    qs = store.products.all().order_by('name')
    if query:
        qs = qs.filter(name__icontains=query)
    if low_stock_only:
        qs = qs.filter(stock__lte=5).order_by('stock')
    return {'products': [{'product_id': p.id, 'name': p.name, 'price': _money(p.price),
                          'stock': p.stock, 'visible': p.is_available} for p in qs[:15]]}


def t_update_product(ctx, product_id, price=None, stock=None, visible=None):
    store = ctx.store()
    if not store:
        return {'error': "Aucun commerce actif lié à ce compte."}
    p = store.products.filter(id=product_id).first()
    if not p:
        return {'error': "Ce produit n'appartient pas à votre commerce."}
    changes, summary = {}, []
    if price not in (None, ''):
        try:
            value = Decimal(str(price))
        except InvalidOperation:
            return {'error': 'Prix invalide.'}
        if value <= 0:
            return {'error': 'Le prix doit être positif.'}
        changes['price'] = str(value)
        summary.append(f"prix {_price(float(p.price))} → {_price(float(value))}")
    if stock not in (None, ''):
        try:
            value = int(stock)
        except (TypeError, ValueError):
            return {'error': 'Stock invalide.'}
        if value < 0:
            return {'error': 'Le stock ne peut pas être négatif.'}
        changes['stock'] = value
        summary.append(f"stock {p.stock} → {value}")
    if visible is not None:
        changes['is_available'] = bool(visible)
        summary.append('visible en boutique' if visible else 'masqué de la boutique')
    if not changes:
        return {'error': 'Aucune modification demandée.'}
    token = signing.dumps({'u': ctx.user.id, 'a': 'update_product', 'p': p.id, 'c': changes}, salt=CONFIRM_SALT)
    label = f"{p.name} : " + ', '.join(summary)
    ctx.confirmations.append({'token': token, 'label': label})
    return {'pending_confirmation': True, 'summary': label,
            'message': "La modification attend que le gérant appuie sur « Confirmer »."}


STORE_ORDER_STEPS = {'confirmed': 'confirmée', 'preparing': 'en préparation', 'ready': 'prête (un livreur sera appelé)',
                     'cancelled': 'annulée'}


def t_set_order_status(ctx, order_number, status_value):
    """Fait avancer une commande du commerce (confirmée → en préparation → prête), après confirmation."""
    store = ctx.store()
    if not store:
        return {'error': "Aucun commerce actif lié à ce compte."}
    order = store.orders.filter(order_number__iexact=str(order_number).strip().lstrip('#')).first()
    if not order:
        return {'error': f"Commande {order_number} introuvable dans votre commerce."}
    if status_value not in STORE_ORDER_STEPS:
        return {'error': 'Statut possible : confirmed, preparing, ready ou cancelled.'}
    from orders.serializers import OrderStatusUpdateSerializer
    check = OrderStatusUpdateSerializer(order, data={'status': status_value}, partial=True)
    if not check.is_valid():
        return {'error': f"Impossible de passer de « {ORDER_STATUS_FR.get(order.status, order.status)} » à "
                         f"« {STORE_ORDER_STEPS[status_value]} »."}
    token = signing.dumps({'u': ctx.user.id, 'a': 'order_status', 'o': order.id, 'st': status_value}, salt=CONFIRM_SALT)
    label = f"Commande {order.order_number} : passer en « {STORE_ORDER_STEPS[status_value]} »"
    ctx.confirmations.append({'token': token, 'label': label})
    return {'pending_confirmation': True, 'summary': label}


def _store_categories(store):
    from products.models import ProductCategory
    return ProductCategory.objects.filter(Q(store=store) | Q(store_category_id=store.category_id)).order_by('order', 'name')


def t_store_categories(ctx):
    store = ctx.store()
    if not store:
        return {'error': "Aucun commerce actif lié à ce compte."}
    return {'categories': [c.name for c in _store_categories(store)]}


def t_create_product(ctx, name, price, stock=1, category=None, brand=None, model=None, color=None,
                     sizes=None, description=None, compare_price=None):
    """Prépare la création d'un produit ; il n'est créé qu'après « Confirmer »."""
    store = ctx.store()
    if not store:
        return {'error': "Aucun commerce actif lié à ce compte."}
    name = str(name or '').strip()[:200]
    if len(name) < 2:
        return {'error': 'Il faut un nom de produit.'}
    try:
        price_value = Decimal(str(price))
    except (InvalidOperation, TypeError):
        return {'error': 'Il faut un prix (en FCFA). Demande-le au gérant.'}
    if price_value <= 0:
        return {'error': 'Le prix doit être positif. Demande-le au gérant.'}
    try:
        stock = max(0, int(stock if stock not in (None, '') else 1))
    except (TypeError, ValueError):
        stock = 1
    from django.core.exceptions import PermissionDenied
    from payments.subscription_check import SubscriptionChecker
    try:
        SubscriptionChecker.check_can_add_product(store)
    except PermissionDenied as exc:
        return {'error': str(exc)}
    cat = None
    if category:
        cats = list(_store_categories(store))
        wanted = _plain(str(category))
        cat = next((c for c in cats if _plain(c.name) == wanted), None) or \
            next((c for c in cats if wanted in _plain(c.name) or _plain(c.name) in wanted), None)
    attrs = {k: str(v).strip()[:100] for k, v in
             (('brand', brand), ('model', model), ('color', color), ('sizes', sizes)) if v not in (None, '')}
    fields = {'name': name, 'price': str(price_value), 'stock': stock, 'category': cat.id if cat else None,
              'attributes': attrs, 'description': str(description or '').strip()[:1000]}
    if compare_price not in (None, ''):
        try:
            cp = Decimal(str(compare_price))
            if cp > price_value:
                fields['compare_price'] = str(cp)
        except InvalidOperation:
            pass
    token = signing.dumps({'u': ctx.user.id, 'a': 'create_product', 's': store.id, 'f': fields}, salt=CONFIRM_SALT)
    details = [f"{stock} en stock", _price(float(price_value))]
    if cat:
        details.append(cat.name)
    details += [v for v in attrs.values()]
    label = f"Créer « {name} » : " + ', '.join(details)
    ctx.confirmations.append({'token': token, 'label': label})
    return {'pending_confirmation': True, 'summary': label,
            'category_found': bool(cat),
            'available_categories': [c.name for c in _store_categories(store)][:20],
            'message': "Le produit sera créé quand le gérant appuiera sur « Confirmer ». "
                       "Il pourra ensuite ajouter une photo dans « Mes produits »."}


def t_my_deliveries(ctx, include_available=True):
    if ctx.user is None:
        return {'error': 'Non connecté.'}
    from delivery.models import Delivery
    mine = Delivery.objects.filter(delivery_agent=ctx.user, status__in=ACTIVE_DELIVERY_STATUSES) \
        .select_related('order__store').order_by('created_at')[:8]
    data = {'my_deliveries': [{
        'tracking': d.tracking_number, 'status': d.get_status_display(),
        'store': d.order.store.name if d.order_id else None,
        'pickup_zone': d.order.store.zone if d.order_id else None,
        'delivery_zone': d.order.delivery_zone if d.order_id else None,
        'address': d.order.delivery_address[:120] if d.order_id else None,
        'phone': d.order.delivery_phone if d.order_id else None,
    } for d in mine]}
    if include_available:
        data['available_count'] = Delivery.objects.filter(
            delivery_agent__isnull=True, status__in=['waiting', 'ready_for_assignment', 'pending']).count()
    data['done_today'] = Delivery.objects.filter(
        delivery_agent=ctx.user, status='delivered', updated_at__date=timezone.localdate()).count()
    return data


def t_platform_stats(ctx, days=7):
    from stores.models import Store
    from users.models import User
    from orders.models import Order
    try:
        days = max(1, min(int(days), 90))
    except (TypeError, ValueError):
        days = 7
    since = timezone.now() - timedelta(days=days)
    orders = Order.objects.filter(created_at__gte=since)
    paid = orders.exclude(status__in=['created', 'pending_payment', 'cancelled', 'refunded'])
    return {
        'period_days': days,
        'orders': orders.count(),
        'paid_orders': paid.count(),
        'sales': _money(paid.aggregate(s=Sum('total_amount'))['s']),
        'commission': _money(paid.aggregate(s=Sum('commission_amount'))['s']),
        'new_clients': User.objects.filter(user_type='client', date_joined__gte=since).count(),
        'stores_active': Store.objects.filter(is_active=True).count(),
        'stores_unverified': Store.objects.filter(is_active=True, is_verified=False).count(),
        'orders_by_status': dict(orders.values_list('status').annotate(n=Count('id')).values_list('status', 'n')),
    }


def t_admin_stores(ctx, unverified_only=False, query=''):
    from stores.models import Store
    qs = Store.objects.select_related('category').annotate(n_products=Count('products')).order_by('-created_at')
    if unverified_only:
        qs = qs.filter(is_verified=False)
    if query:
        qs = qs.filter(name__icontains=query)
    return {'stores': [{'store_id': s.id, 'name': s.name, 'category': s.category.name if s.category_id else None,
                        'zone': s.zone, 'active': s.is_active, 'verified': s.is_verified,
                        'products': s.n_products} for s in qs[:10]]}


def t_recent_orders(ctx, status_filter=''):
    from orders.models import Order
    qs = Order.objects.select_related('store').prefetch_related('items__product').order_by('-created_at')
    if status_filter in ORDER_STATUS_FR:
        qs = qs.filter(status=status_filter)
    return {'orders': [_order_payload(o) for o in qs[:8]]}


def _schema(name, description, properties=None, required=None):
    return {'type': 'function', 'function': {
        'name': name, 'description': description,
        'parameters': {'type': 'object', 'properties': properties or {}, 'required': required or []},
    }}


_INT = {'type': 'integer'}
_NUM = {'type': 'number'}
_STR = {'type': 'string'}
_BOOL = {'type': 'boolean'}
SHOPPER = ('visitor', 'client')
EVERYONE = ('visitor', 'client', 'store_manager', 'delivery_agent', 'admin')

TOOLS = {
    'search_products': (EVERYONE, t_search_products, _schema(
        'search_products', "Chercher des produits dans le catalogue Gaboshop. Utiliser des mots simples (ex: 'basket', 'riz').",
        {'query': {**_STR, 'description': 'mots-clés du produit'}, 'max_price': _NUM, 'min_price': _NUM,
         'brand': {**_STR, 'description': 'marque, ex: Adidas'}, 'size': {**_STR, 'description': 'taille ou pointure'},
         'in_stock': _BOOL, 'store_id': _INT})),
    'get_product': (EVERYONE, t_get_product, _schema(
        'get_product', 'Détails complets d\'un produit (description, tailles, stock).',
        {'product_id': _INT}, ['product_id'])),
    'add_to_cart': (SHOPPER, t_add_to_cart, _schema(
        'add_to_cart', 'Ajouter un produit au panier du client. Seulement quand le produit voulu est clair.',
        {'product_id': _INT, 'quantity': _INT, 'size': _STR}, ['product_id'])),
    'remove_from_cart': (SHOPPER, t_remove_from_cart, _schema(
        'remove_from_cart', 'Retirer un produit du panier.', {'product_id': _INT}, ['product_id'])),
    'view_cart': (SHOPPER, t_view_cart, _schema('view_cart', 'Voir le contenu et le total du panier.')),
    'my_orders': (('client',), t_my_orders, _schema(
        'my_orders', 'Voir les dernières commandes du client et leur statut.', {'active_only': _BOOL})),
    'info': (EVERYONE, t_info, _schema(
        'info', 'Informations Gaboshop : livraison, paiement, suivi, compte, retours, horaires.',
        {'topic': _STR}, ['topic'])),
    'open_page': (EVERYONE, t_open_page, _schema(
        'open_page', "Ouvrir une page de l'application pour l'utilisateur.",
        {'page': {**_STR, 'enum': sorted(list(PAGES) + ['store', 'product'])}, 'store_id': _INT, 'product_id': _INT},
        ['page'])),
    'store_overview': (('store_manager',), t_store_overview, _schema(
        'store_overview', 'Résumé du commerce : ventes, commandes à traiter, stock faible, profil incomplet.')),
    'store_orders': (('store_manager',), t_store_orders, _schema(
        'store_orders', 'Commandes du commerce. status_filter: to_handle (par défaut), all, ou un statut.',
        {'status_filter': _STR})),
    'store_products': (('store_manager',), t_store_products, _schema(
        'store_products', 'Liste des produits du commerce (prix, stock, visibilité).',
        {'query': _STR, 'low_stock_only': _BOOL})),
    'update_product': (('store_manager',), t_update_product, _schema(
        'update_product', "Préparer une modification de prix, de stock ou de visibilité d'un produit du commerce. "
                          "Le gérant devra confirmer d'un bouton.",
        {'product_id': _INT, 'price': _NUM, 'stock': _INT, 'visible': _BOOL}, ['product_id'])),
    'set_order_status': (('store_manager',), t_set_order_status, _schema(
        'set_order_status', "Faire avancer une commande du commerce : confirmed, preparing, ready (appelle un livreur) "
                            "ou cancelled. Le gérant confirme d'un bouton.",
        {'order_number': _STR, 'status_value': {**_STR, 'enum': list(STORE_ORDER_STEPS)}},
        ['order_number', 'status_value'])),
    'store_categories': (('store_manager',), t_store_categories, _schema(
        'store_categories', 'Catégories de produits disponibles pour ce commerce.')),
    'create_product': (('store_manager',), t_create_product, _schema(
        'create_product', "Créer un NOUVEAU produit dans le commerce du gérant (ex: « ajoute 10 All Star noires à "
                          "25000 F »). Le prix est obligatoire : s'il manque, demande-le d'abord. Rédige une courte "
                          "description vendeuse. Le gérant confirme d'un bouton.",
        {'name': {**_STR, 'description': 'nom du produit, ex: Converse All Star'}, 'price': _NUM,
         'stock': {**_INT, 'description': 'quantité disponible'}, 'category': _STR, 'brand': _STR, 'model': _STR,
         'color': _STR, 'sizes': {**_STR, 'description': 'tailles ou pointures séparées par des virgules'},
         'description': _STR, 'compare_price': {**_NUM, 'description': 'ancien prix si promotion'}},
        ['name', 'price'])),
    'my_deliveries': (('delivery_agent',), t_my_deliveries, _schema(
        'my_deliveries', 'Livraisons en cours du livreur, adresses, et nombre de livraisons disponibles.',
        {'include_available': _BOOL})),
    'platform_stats': (('admin',), t_platform_stats, _schema(
        'platform_stats', 'Chiffres de la plateforme sur une période (jours).', {'days': _INT})),
    'admin_stores': (('admin',), t_admin_stores, _schema(
        'admin_stores', 'Liste des commerces (filtrer les non vérifiés).', {'unverified_only': _BOOL, 'query': _STR})),
    'recent_orders': (('admin',), t_recent_orders, _schema(
        'recent_orders', 'Dernières commandes de la plateforme.', {'status_filter': _STR})),
}


def tools_for(role):
    return {name: spec for name, spec in TOOLS.items() if role in spec[0]}


def run_tool(ctx, name, args):
    spec = tools_for(ctx.role).get(name)
    if not spec:
        return {'error': f"Outil non autorisé : {name}"}
    if not isinstance(args, dict):
        args = {}
    try:
        return spec[1](ctx, **args)
    except TypeError as exc:
        return {'error': f"Paramètres invalides : {exc}"}
    except Exception as exc:  # un outil ne doit jamais faire tomber la conversation
        logger.exception('Outil IA %s', name)
        return {'error': f"Erreur interne : {exc.__class__.__name__}"}


# ---------------------------------------------------------------------------
# Modèle (Groq, compatible OpenAI)
# ---------------------------------------------------------------------------

ROLE_GUIDE = {
    'visitor': "C'est un visiteur. Aide-le à trouver et choisir des produits. Pour ajouter au panier il doit se "
               "connecter : utilise quand même add_to_cart, l'application lui proposera de se connecter.",
    'client': "C'est un client connecté. Accompagne-le jusqu'au panier : comprendre son besoin, chercher, comparer, "
              "conseiller (taille, budget), ajouter au panier, puis l'inviter à valider sa commande. "
              "Tu peux aussi suivre ses commandes.",
    'store_manager': "C'est le gérant d'un commerce. Aide-le à gérer sa boutique : commandes à préparer, stock faible, "
                     "prix, produits masqués, conseils de vente. Pour AJOUTER un produit à sa boutique, utilise "
                     "create_product (search_products cherche seulement dans tout le marché, ce n'est pas un ajout). "
                     "Pour faire avancer une commande (confirmer, préparer, prête) utilise set_order_status. "
                     "Créations et modifications attendent sa confirmation par un bouton. Les photos s'ajoutent "
                     "ensuite dans « Mes produits » (open_page store_products).",
    'delivery_agent': "C'est un livreur. Aide-le à organiser ses livraisons : adresses, contacts, ordre de passage, "
                      "livraisons disponibles.",
    'admin': "C'est l'administrateur de Gaboshop. Donne des chiffres précis, repère les problèmes (commerces non "
             "vérifiés, commandes bloquées) et propose des actions.",
}


def system_prompt(ctx, page):
    name = ''
    if ctx.user is not None:
        name = (ctx.user.first_name or '').strip()
    return f"""Tu es l'assistant intégré de Gaboshop, une place de marché en ligne au Gabon (Libreville).
Tu es le meilleur utilisateur de l'application : tu agis avec les outils au lieu d'expliquer où cliquer.
Utilisateur : {ROLE_LABELS.get(ctx.role, ctx.role)}{f' ({name})' if name else ''}. Page actuelle : {page or 'inconnue'}.
{ROLE_GUIDE.get(ctx.role, '')}

Règles :
- Réponds en français, chaleureux et bref (1 à 4 phrases). Tutoiement interdit, vouvoie.
- Conversation normale (bonjour, ça va, merci) : réponds naturellement, sans chercher de produit.
- Avant de parler d'un produit, d'un prix, d'un stock ou d'une commande, appelle l'outil adapté. N'invente jamais rien.
- Recherche : mots simples au singulier ; mets la marque dans brand, la taille dans size, le budget dans max_price.
  Si rien n'est trouvé, réessaie avec un mot plus général ou un synonyme avant de conclure.
- Les produits trouvés s'affichent en cartes sous ta réponse : ne recopie pas toute la liste, conseille.
- Si la demande est ambiguë (plusieurs produits possibles, taille manquante pour un vêtement), pose UNE question courte.
- Quand le client veut un produit précis, ajoute-le au panier avec add_to_cart (quantité et taille demandées).
- Les modifications de prix/stock attendent la confirmation de l'utilisateur : dis-le.
- Montants en FCFA."""


def _client(config):
    import openai
    return openai.OpenAI(api_key=config['api_key'], base_url=config.get('base_url'), timeout=20, max_retries=0)


FALLBACK_MODELS = ['openai/gpt-oss-120b', 'openai/gpt-oss-20b', 'llama-3.3-70b-versatile', 'llama-3.1-8b-instant']
MODEL_RETRY_AFTER = 3600  # un modèle en échec n'est retenté qu'au bout d'une heure
_MODEL_STATE = {'working': None, 'failed': {}}


def candidate_models(config):
    """Le dernier modèle qui a marché d'abord, puis les autres ; ceux en échec récent passent en dernier."""
    preferred = [_MODEL_STATE['working'], config.get('model')] + FALLBACK_MODELS
    ordered = []
    for m in preferred:
        if m and m not in ordered:
            ordered.append(m)
    now = timezone.now()
    fresh = [m for m in ordered if not (m in _MODEL_STATE['failed']
             and (now - _MODEL_STATE['failed'][m][0]).total_seconds() < MODEL_RETRY_AFTER)]
    return fresh + [m for m in ordered if m not in fresh]


def mark_model(model, error=None):
    if error is None:
        _MODEL_STATE['working'] = model
        _MODEL_STATE['failed'].pop(model, None)
    else:
        _MODEL_STATE['failed'][model] = (timezone.now(), str(error)[:200])
        if _MODEL_STATE['working'] == model:
            _MODEL_STATE['working'] = None


def model_options(model, max_tokens):
    """Les modèles gpt-oss « réfléchissent » avant de répondre : on limite cette réflexion."""
    if 'gpt-oss' in model:
        return {'max_tokens': max_tokens * 3, 'extra_body': {'reasoning_effort': 'low'}}
    return {'max_tokens': max_tokens}


_LAST_STATUS = {}


def record_status(ok, provider, model=None, error=None):
    data = {
        'ok': ok, 'provider': provider, 'model': model,
        'error': (str(error)[:300] if error else None),
        'at': timezone.now().isoformat(),
    }
    # Copie en mémoire (un seul processus sur Render) au cas où le cache Redis manque
    _LAST_STATUS.clear()
    _LAST_STATUS.update(data)
    try:
        cache.set(STATUS_CACHE_KEY, data, 24 * 3600)
    except Exception:
        pass


def live_check(config):
    """Petit appel réel à Groq pour savoir tout de suite si la clé et le modèle marchent."""
    client = _client(config)
    last_error = None
    for model in candidate_models(config):
        try:
            resp = client.chat.completions.create(
                model=model, messages=[{'role': 'user', 'content': 'Réponds seulement: OK'}],
                **model_options(model, 20))
            mark_model(model)
            record_status(True, config['name'], model)
            return {'ok': True, 'model': model, 'answer': (resp.choices[0].message.content or '').strip()[:20]}
        except Exception as exc:
            last_error = exc
            if any(k in str(exc).lower() for k in ('invalid api key', 'invalid_api_key', '401', 'authentication')):
                break
            mark_model(model, exc)
    record_status(False, config['name'], error=last_error)
    return {'ok': False, 'error': str(last_error)[:300]}


def run_llm(ctx, message, history, page, config):
    """Boucle agent : le modèle appelle des outils jusqu'à pouvoir répondre. Renvoie le texte ou None."""
    client = _client(config)
    tools = [spec[2] for spec in tools_for(ctx.role).values()]
    messages = [{'role': 'system', 'content': system_prompt(ctx, page)}]
    for h in history[-8:]:
        if isinstance(h, dict) and h.get('text'):
            messages.append({'role': 'user' if h.get('role') == 'user' else 'assistant',
                             'content': str(h['text'])[:600]})
    messages.append({'role': 'user', 'content': message})

    last_error = None
    for model in candidate_models(config)[:3]:
        convo = list(messages)
        # Repartir de zéro : un essai raté ne doit pas laisser d'actions en double (panier)
        ctx.products, ctx.actions, ctx.confirmations = {}, [], []
        try:
            for _ in range(MAX_STEPS):
                resp = client.chat.completions.create(
                    model=model, messages=convo, tools=tools, tool_choice='auto',
                    temperature=0.3, **model_options(model, 700),
                )
                msg = resp.choices[0].message
                calls = msg.tool_calls or []
                if not calls:
                    text = (msg.content or '').strip()
                    if not text:
                        raise ValueError('réponse vide')
                    mark_model(model)
                    record_status(True, config['name'], model)
                    return text
                convo.append({'role': 'assistant', 'content': msg.content or '', 'tool_calls': [
                    {'id': c.id, 'type': 'function',
                     'function': {'name': c.function.name, 'arguments': c.function.arguments or '{}'}}
                    for c in calls]})
                for c in calls:
                    try:
                        args = json.loads(c.function.arguments or '{}')
                    except ValueError:
                        args = {}
                    result = run_tool(ctx, c.function.name, args)
                    convo.append({'role': 'tool', 'tool_call_id': c.id,
                                  'content': json.dumps(result, ensure_ascii=False, default=str)[:4000]})
            # Trop d'étapes : on demande une réponse finale sans outil
            resp = client.chat.completions.create(model=model, messages=convo, temperature=0.3,
                                                  **model_options(model, 500))
            text = (resp.choices[0].message.content or '').strip()
            if not text:
                raise ValueError('réponse vide')
            mark_model(model)
            record_status(True, config['name'], model)
            return text
        except Exception as exc:
            last_error = exc
            logger.warning('Assistant IA : échec avec %s : %s', model, exc)
            text = str(exc).lower()
            # Clé refusée : inutile d'essayer un autre modèle
            if any(k in text for k in ('invalid api key', 'invalid_api_key', '401', 'authentication')):
                break
            mark_model(model, exc)
            continue
    record_status(False, config['name'], error=last_error)
    return None


# ---------------------------------------------------------------------------
# Moteur local (sans IA externe)
# ---------------------------------------------------------------------------

SMALL_TALK = [
    (r"\b(comment (vas|allez|ca va)|ca va|tu vas bien|vous allez bien)\b",
     "Je vais très bien, merci ! Et vous ? Dites-moi ce que vous cherchez, je m'occupe du reste."),
    (r"\b(merci|thanks)\b", "Avec plaisir ! Autre chose pour vous ?"),
    (r"\b(qui es[- ]tu|qui etes[- ]vous|tu es qui)\b",
     "Je suis l'assistant de Gaboshop : je cherche les produits, je les ajoute à votre panier et je suis vos commandes."),
    (r"^(ok|d'accord|daccord|super|top|cool|parfait)\W*$", "Parfait ! Je reste là si besoin."),
    (r"\b(au revoir|bye|a plus|bonne (journee|soiree))\b", "À bientôt sur Gaboshop !"),
]
ADD_RE = re.compile(r"\b(ajout\w*|mets?|met|command\w*|achet\w*|prend\w*|je (le|la|les) veux|panier)\b")
QTY_WORDS = {'un': 1, 'une': 1, 'deux': 2, 'trois': 3, 'quatre': 4, 'cinq': 5, 'six': 6, 'dix': 10}


def _quantity(text):
    m = re.search(r"\b(\d{1,2})\s*(?:x\b|fois\b|pieces?\b|unites?\b|paires?\b)?", text)
    if m and not re.search(r"(taille|pointure)\s*" + m.group(1), text):
        return int(m.group(1))
    for w, n in QTY_WORDS.items():
        if re.search(rf"\b{w}\b", text) and w not in ('un', 'une'):
            return n
    return 1


def _size(text):
    m = re.search(r"\b(?:taille|pointure|size)\s*([a-z0-9]{1,4})\b", text)
    return m.group(1).upper() if m else None


def local_engine(ctx, message):
    text = _plain(message)
    for pattern, answer in SMALL_TALK:
        if re.search(pattern, text):
            return answer
    if re.search(r"^(bonjour|salut|bonsoir|hello|coucou|hey)\W*$", text):
        intro = {
            'store_manager': "Bonjour ! Je peux vous résumer votre boutique, vos commandes à préparer ou votre stock faible.",
            'delivery_agent': "Bonjour ! Je peux vous donner vos livraisons en cours et celles disponibles.",
            'admin': "Bonjour ! Je peux vous donner les chiffres de la plateforme et les commerces à vérifier.",
        }.get(ctx.role)
        return intro or ("Bonjour ! Dites-moi ce que vous cherchez (par exemple « riz moins de 5000 F » "
                         "ou « baskets Adidas taille 42 ») et je vous montre les produits.")

    if ctx.role == 'store_manager':
        return _local_store(ctx, text) or _local_shop(ctx, message, text)
    if ctx.role == 'delivery_agent' and re.search(r"livr|course|colis|adresse|aujourd", text):
        return _local_delivery(ctx)
    if ctx.role == 'admin' and re.search(r"chiffre|stat|vente|commande|commerce|boutique|magasin|bilan", text):
        return _local_admin(ctx, text)
    if ctx.role == 'client' and re.search(r"\b(ma|mes) commandes?\b|suivi|ou en est", text):
        orders = t_my_orders(ctx, active_only=False).get('orders') or []
        if not orders:
            return "Vous n'avez pas encore de commande."
        o = orders[0]
        return f"Votre dernière commande {o['order_number']} ({o['store']}) est {o['status']}, total {_price(o['total'])}."
    if re.search(r"\b(mon|le) panier\b", text) and not ADD_RE.search(text.replace('panier', '')):
        cart = t_view_cart(ctx)
        if not cart['items']:
            return "Votre panier est vide. Que cherchez-vous ?"
        return f"Votre panier contient {len(cart['items'])} article(s) pour {_price(cart['items_total'])}."
    return _local_shop(ctx, message, text)


def _local_shop(ctx, message, text):
    faq = faq_answer(message)
    criteria = extract_criteria(message)
    size = _size(text)
    criteria['keywords'] = [k for k in criteria['keywords']
                            if k not in ('commande', 'moi', 'ajoute', 'ajouter', 'mets', 'met', 'veux', 'prends', 'size')
                            and not (size and k.upper() == size)]
    found = search_catalog(criteria) if criteria['keywords'] or criteria['max_price'] else []
    if not found and criteria['keywords']:
        # Mot inconnu dans les noms : on essaie chaque mot seul (marque, couleur…)
        for k in criteria['keywords']:
            found = search_catalog({**criteria, 'keywords': [k]})
            if found:
                break
    exact, partial = split_matches(found, criteria['keywords'])
    missing = []
    if not exact and partial and len(criteria['keywords']) > 1:
        missing = [k for k in criteria['keywords'] if not any(k in _blob(p) for p in partial)]
    shown = exact or found
    ctx.show(shown)
    if shown and ADD_RE.search(text) and ctx.role in SHOPPER and not missing:
        if len(shown) == 1:
            qty = _quantity(text)
            result = t_add_to_cart(ctx, shown[0].id, qty, size)
            if result.get('ok'):
                return f"C'est fait : {result['added']}{f' (taille {size})' if size else ''} ajouté à votre panier."
            if result.get('needs_login'):
                return "Connectez-vous ou créez un compte gratuit pour ajouter ce produit : il sera ajouté juste après."
            return result.get('error', '')
        return f"J'ai trouvé {len(shown)} produits possibles : touchez « + Panier » sur celui que vous voulez."
    if shown:
        n = len(shown)
        cheapest = min(float(p.price) for p in shown)
        stores = sorted({p.store.name for p in shown})
        where = stores[0] if len(stores) == 1 else f"{len(stores)} commerces"
        head = ''
        if missing:
            head = f"Je n'ai rien trouvé avec « {' '.join(missing)} ». Voici des produits proches : "
            return head + f"{n} produit{'s' if n > 1 else ''} chez {where}, à partir de {_price(cheapest)}."
        return ((faq + "\n\n") if faq else '') + (
            f"J'ai trouvé {n} produit{'s' if n > 1 else ''} chez {where}, à partir de {_price(cheapest)}. "
            "Touchez un produit pour voir sa fiche, ou « + Panier » pour l'ajouter.")
    if faq:
        return faq
    if criteria['keywords']:
        return (f"Je n'ai trouvé aucun produit pour « {' '.join(criteria['keywords'])} ». "
                "Essayez un mot plus simple (ex. « basket », « riz ») ou un autre budget.")
    return ("Je peux chercher des produits, les ajouter à votre panier et suivre vos commandes. "
            "Que cherchez-vous ?")


COLORS = ['noir', 'noire', 'blanc', 'blanche', 'rouge', 'bleu', 'bleue', 'vert', 'verte', 'jaune', 'gris', 'grise',
          'rose', 'marron', 'beige', 'orange', 'violet', 'violette', 'dore', 'doree', 'argent']
CREATE_RE = re.compile(r"\b(ajout\w*|cree\w*|creer|nouveau produit|mets? en vente|met en vente|enregistre\w*)\b")


def _local_create_product(ctx, text):
    """« ajoute 10 all star noires à 25000 F taille 38 à 44 » → proposition de création."""
    price = None
    m = re.search(r"(?:a|prix(?: de)?|pour|vendu(?:es?)? a)\s*(\d+(?:[ .]\d{3})*)\s*(?:f\b|fcfa|cfa|francs?)?", text) \
        or re.search(r"(\d+(?:[ .]\d{3})*)\s*(?:f\b|fcfa|cfa|francs?)", text)
    if m:
        price = int(re.sub(r"[ .]", '', m.group(1)))
        text_wo_price = text.replace(m.group(0), ' ')
    else:
        text_wo_price = text
    sizes = None
    m = re.search(r"(?:tailles?|pointures?)\s*(\d{1,2}\s*(?:a|-|au)\s*\d{1,2}|[a-z0-9 ,]+?)(?=$|\s(?:a|prix|couleur|de couleur)\b)", text_wo_price)
    if m:
        sizes = re.sub(r"\s*(?:a|-|au)\s*", '-', m.group(1).strip()) if re.search(r"\d\s*(a|-|au)\s*\d", m.group(1)) else m.group(1).strip()
        text_wo_price = text_wo_price.replace(m.group(0), ' ')
    stock = 1
    m = re.search(r"\b(\d{1,4})\b", text_wo_price)
    if m:
        stock = int(m.group(1))
        text_wo_price = text_wo_price.replace(m.group(0), ' ', 1)
    color = next((c for c in COLORS if re.search(rf"\b{c}s?\b", text_wo_price)), None)
    words = [w for w in re.findall(r"[a-z0-9']+", CREATE_RE.sub(' ', text_wo_price))
             if w not in STOP_CREATE and not (color and w.rstrip('s') == color)]
    name = ' '.join(words).strip()
    if len(name) < 3:
        return ("Je peux créer le produit pour vous. Dites-moi son nom, son prix et la quantité, par exemple : "
                "« ajoute 10 All Star noires à 25 000 F, tailles 38 à 44 ».")
    name = name.title()
    if price is None:
        return f"D'accord pour « {name} »{f' ({stock})' if stock > 1 else ''}. À quel prix le vendez-vous ? Répétez la demande avec le prix, par exemple « ajoute {stock} {name.lower()} à 25 000 F »."
    result = t_create_product(ctx, name=name, price=price, stock=stock,
                              color=(color.capitalize() if color else None), sizes=sizes)
    if result.get('error'):
        return result['error']
    return f"Je prépare « {name} » : {stock} en stock à {_price(price)}. Appuyez sur « Confirmer » pour le mettre en vente."


STOP_CREATE = {'je', 'veux', 'que', 'tu', 'vous', 'fasses', 'fassiez', 'fais', 'faites', 'l', 'le', 'la', 'les', 'un',
               'une', 'des', 'de', 'du', 'd', 'au', 'aux', 'a', 'mon', 'ma', 'mes', 'magasin', 'boutique', 'stock',
               'produit', 'produits', 'nouveau', 'nouvelle', 'nouveaux', 'en', 'vente', 'dans', 'pour', 'svp', 'stp',
               'couleur', 'peux', 'pouvez', 'moi', 'me', 'merci', 'aussi', 'et', 'avec', 'pieces', 'piece', 'unites',
               'paires', 'paire', 'exemplaires', 'catalogue'}


def _local_store(ctx, text):
    if CREATE_RE.search(text):
        return _local_create_product(ctx, text)
    if not re.search(r"vente|chiffre|commande|stock|bilan|resume|boutique|magasin|produit|rupture", text):
        return None
    data = t_store_overview(ctx)
    if data.get('error'):
        return data['error']
    parts = [f"{data['store']} : {data['orders_last_7_days']} commande(s) sur 7 jours pour {_price(data['sales_last_7_days'])}",
             f"{data['orders_to_handle']} commande(s) à préparer"]
    if data['low_stock']:
        parts.append("stock faible : " + ', '.join(f"{p['name']} ({p['stock']})" for p in data['low_stock'][:4]))
    if not data['has_logo'] or not data['has_description']:
        parts.append("pensez à compléter le logo et la description de la boutique")
    return '. '.join(parts) + '.'


def _local_delivery(ctx):
    data = t_my_deliveries(ctx)
    if data.get('error'):
        return data['error']
    mine = data['my_deliveries']
    if not mine:
        return f"Aucune livraison en cours. {data.get('available_count', 0)} livraison(s) disponible(s) à accepter."
    lines = [f"Vous avez {len(mine)} livraison(s) en cours :"]
    for d in mine:
        lines.append(f"• {d['store']} → {d['delivery_zone']} ({d['status']}), tél. {d['phone']}")
    return '\n'.join(lines)


def _local_admin(ctx, text):
    if re.search(r"commerce|boutique|magasin|verif", text):
        stores = t_admin_stores(ctx, unverified_only=True)['stores']
        if not stores:
            return "Tous les commerces sont vérifiés."
        return "Commerces à vérifier : " + ', '.join(s['name'] for s in stores) + '.'
    s = t_platform_stats(ctx)
    return (f"Sur 7 jours : {s['orders']} commande(s), dont {s['paid_orders']} payée(s), {_price(s['sales'])} de ventes, "
            f"{_price(s['commission'])} de commission. {s['new_clients']} nouveau(x) client(s), "
            f"{s['stores_unverified']} commerce(s) à vérifier.")


# ---------------------------------------------------------------------------
# Points d'accès
# ---------------------------------------------------------------------------

def _clean_cart(raw):
    cart = []
    if isinstance(raw, list):
        for item in raw[:50]:
            if isinstance(item, dict) and item.get('id'):
                cart.append({k: item.get(k) for k in ('id', 'name', 'price', 'quantity', 'store_name')})
    return cart


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@throttle_classes([ShopAnonThrottle, ShopUserThrottle])
def ai_assistant(request):
    """
    POST /api/v1/ai/assistant/
    Body : {"message", "history": [{"role","text"}], "cart": [...], "page": "/..."}
    Réponse : {"message", "products": [...], "actions": [...], "confirmations": [...], "provider"}
    """
    message = str(request.data.get('message', '')).strip()[:600]
    if not message:
        return Response({'success': False, 'error': {'message': 'Écrivez votre question.'}},
                        status=status.HTTP_400_BAD_REQUEST)
    history = request.data.get('history') or []
    history = history if isinstance(history, list) else []
    page = str(request.data.get('page') or '')[:100]
    role = user_role(request.user)
    ctx = Ctx(request, role, _clean_cart(request.data.get('cart')))

    from .providers import AIProvider
    config = AIProvider.get_provider_config()
    reply, provider = None, 'local'
    if config.get('available') and config.get('name') != 'local':
        reply = run_llm(ctx, message, history, page, config)
        if reply:
            provider = config['name']
        else:
            # On repart de zéro pour que le moteur local ne mélange pas ses résultats avec ceux du modèle
            ctx = Ctx(request, role, ctx.cart)
    if not reply:
        reply = local_engine(ctx, message)

    return Response({'success': True, 'data': {
        'message': reply,
        'products': list(ctx.products.values())[:8],
        'actions': ctx.actions,
        'confirmations': ctx.confirmations,
        'provider': provider,
        'role': role,
    }})


_USED_TOKENS = {}  # une création confirmée ne peut pas être rejouée (double appui)


def _cache_get(key):
    try:
        return cache.get(key)
    except Exception:
        return None


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def ai_assistant_confirm(request):
    """POST /api/v1/ai/assistant/confirm/ {"token"} : exécute une modification proposée par l'assistant."""
    try:
        data = signing.loads(str(request.data.get('token', '')), salt=CONFIRM_SALT, max_age=CONFIRM_MAX_AGE)
    except signing.SignatureExpired:
        return Response({'success': False, 'error': {'message': 'Cette proposition a expiré, redemandez-la.'}},
                        status=status.HTTP_400_BAD_REQUEST)
    except signing.BadSignature:
        return Response({'success': False, 'error': {'message': 'Action invalide.'}}, status=status.HTTP_400_BAD_REQUEST)
    if data.get('u') != request.user.id:
        return Response({'success': False, 'error': {'message': 'Action non autorisée.'}}, status=status.HTTP_403_FORBIDDEN)
    if data.get('a') == 'order_status':
        from orders.models import Order
        from orders.serializers import OrderStatusUpdateSerializer
        order = Order.objects.filter(id=data.get('o'), store__manager=request.user).first()
        if not order:
            return Response({'success': False, 'error': {'message': 'Commande introuvable.'}}, status=status.HTTP_404_NOT_FOUND)
        serializer = OrderStatusUpdateSerializer(order, data={'status': data.get('st')}, partial=True)
        if not serializer.is_valid():
            return Response({'success': False, 'error': {'message': "Ce changement n'est plus possible (la commande a changé)."}},
                            status=status.HTTP_400_BAD_REQUEST)
        if data.get('st') == 'ready':
            from payments.direct_service import can_dispatch
            if not can_dispatch(order):
                return Response({'success': False, 'error': {'message': "Le paiement requis avant l'expédition n'est pas confirmé."}},
                                status=status.HTTP_409_CONFLICT)
        serializer.save()
        order.refresh_from_db()
        if order.status == 'ready':
            try:
                from api.v1.orders import auto_assign_delivery
                auto_assign_delivery(order)
            except Exception:
                logger.exception('Assignation livreur après action IA')
        return Response({'success': True, 'data': {
            'message': f"C'est fait : commande {order.order_number} {ORDER_STATUS_FR.get(order.status, order.status)}.",
            'path': '/store/orders',
        }})
    if data.get('a') == 'create_product':
        from django.core.exceptions import PermissionDenied
        from payments.subscription_check import SubscriptionChecker
        from products.models import ProductCategory
        from stores.models import Store
        store = Store.objects.filter(id=data.get('s'), manager=request.user, is_active=True).first()
        if not store:
            return Response({'success': False, 'error': {'message': 'Commerce introuvable.'}}, status=status.HTTP_404_NOT_FOUND)
        f = data.get('f') or {}
        cat = ProductCategory.objects.filter(id=f.get('category')).first() if f.get('category') else None
        try:
            SubscriptionChecker.check_can_add_product(store)
            SubscriptionChecker.check_can_add_non_food_product(store, cat)
        except PermissionDenied as exc:
            return Response({'success': False, 'error': {'message': str(exc)}}, status=status.HTTP_403_FORBIDDEN)
        used_key = 'ai_confirm_used:' + hashlib.sha256(str(request.data.get('token')).encode()).hexdigest()
        if _USED_TOKENS.get(used_key) or _cache_get(used_key):
            return Response({'success': False, 'error': {'message': 'Ce produit a déjà été créé.'}},
                            status=status.HTTP_400_BAD_REQUEST)
        product = Product.objects.create(
            store=store, name=f['name'], price=Decimal(f['price']), stock=int(f.get('stock') or 0),
            category=cat, description=f.get('description', ''), attributes=f.get('attributes') or {},
            compare_price=Decimal(f['compare_price']) if f.get('compare_price') else None,
        )
        _USED_TOKENS[used_key] = True
        try:
            cache.set(used_key, True, CONFIRM_MAX_AGE)
        except Exception:
            pass
        return Response({'success': True, 'data': {
            'message': f"C'est fait : « {product.name} » est en vente dans votre boutique. "
                       "Ajoutez-lui une photo dans « Mes produits ».",
            'path': '/store/products',
        }})
    if data.get('a') == 'update_product':
        p = Product.objects.filter(id=data.get('p'), store__manager=request.user).first()
        if not p:
            return Response({'success': False, 'error': {'message': 'Produit introuvable.'}}, status=status.HTTP_404_NOT_FOUND)
        changes = data.get('c') or {}
        if 'price' in changes:
            p.price = Decimal(changes['price'])
        if 'stock' in changes:
            p.stock = int(changes['stock'])
        if 'is_available' in changes:
            p.is_available = bool(changes['is_available'])
        p.save()
        return Response({'success': True, 'data': {'message': f"C'est fait : {p.name} mis à jour."}})
    return Response({'success': False, 'error': {'message': 'Action inconnue.'}}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def ai_assistant_status(request):
    """GET /api/v1/ai/assistant/status/ : l'IA externe est-elle configurée et fonctionne-t-elle ? (sans secret)"""
    from .providers import AIProvider
    config = AIProvider.get_provider_config()
    last = None
    try:
        last = cache.get(STATUS_CACHE_KEY)
    except Exception:
        pass
    data = {
        'provider': config.get('name'),
        'key_present': bool(config.get('api_key')),
        'model': config.get('model'),
        'last_call': last or (dict(_LAST_STATUS) if _LAST_STATUS else None),
    }
    # ?test=1 : essai réel, limité à une fois par minute pour ne pas gaspiller le quota gratuit
    if request.query_params.get('test') and config.get('available') and config.get('name') != 'local':
        now = timezone.now()
        last_test = _LAST_STATUS.get('_tested_at')
        if last_test and (now - last_test).total_seconds() < 60:
            data['test'] = {'skipped': 'Un essai par minute maximum, réessayez plus tard.'}
        else:
            data['test'] = live_check(config)
            _LAST_STATUS['_tested_at'] = now
            data['last_call'] = {k: v for k, v in _LAST_STATUS.items() if not k.startswith('_')}
    data['working_model'] = _MODEL_STATE['working']
    data['failed_models'] = {m: err for m, (_, err) in _MODEL_STATE['failed'].items()}
    if isinstance(data['last_call'], dict):
        data['last_call'] = {k: v for k, v in data['last_call'].items() if not str(k).startswith('_')}
    return Response({'success': True, 'data': data})
