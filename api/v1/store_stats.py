"""Statistiques avancées du commerçant : outil des forfaits Pro et Business (payments/plan_features.py).

Le forfait Gratuit reçoit seulement le résumé de la période (ventes, commandes, panier moyen) avec le message
qui explique comment débloquer le reste. Les jours et les heures sont ceux de Libreville.
"""
from collections import defaultdict
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Min, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from orders.models import Order, OrderItem
from payments.plan_features import has, required_message
from products.models import Product
from stores.models import LIBREVILLE_TZ, Store

# Une commande compte comme une vente dès que le paiement ou la confirmation est acquis.
SOLD = ('paid', 'confirmed', 'preparing', 'ready', 'assigned', 'in_transit', 'delivered')
PERIODS = (7, 30, 90)
WEEKDAYS = ('lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche')
ZERO = Decimal('0')


def _money(value):
    return int(Decimal(value or 0).quantize(Decimal('1')))


def _change(now, before):
    if not before:
        return None
    return round((Decimal(now) - Decimal(before)) * 100 / Decimal(before))


def _summary(current, previous):
    agg = current.aggregate(revenue=Coalesce(Sum('items_total'), ZERO), orders=Count('id'))
    prev = previous.aggregate(revenue=Coalesce(Sum('items_total'), ZERO), orders=Count('id'))
    orders = agg['orders']
    return {
        'revenue': _money(agg['revenue']),
        'orders': orders,
        'average_basket': _money(agg['revenue'] / orders) if orders else 0,
        'previous_revenue': _money(prev['revenue']),
        'previous_orders': prev['orders'],
        'revenue_change_percent': _change(agg['revenue'], prev['revenue']),
        'orders_change_percent': _change(orders, prev['orders']),
    }


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def store_stats(request):
    """GET /api/v1/store/stats/?days=7|30|90"""
    store = Store.objects.filter(manager=request.user).first()
    if store is None:
        return Response({'success': False, 'error': {
            'code': 'no_store', 'message': "Aucune boutique n'est liée à votre compte.",
            'next_step': 'Créez votre boutique depuis votre espace commerçant.'}}, status=status.HTTP_403_FORBIDDEN)
    try:
        days = int(request.query_params.get('days', 30))
    except (TypeError, ValueError):
        days = 30
    if days not in PERIODS:
        days = 30

    # La période couvre des journées entières de Libreville (aujourd'hui compris), comme le graphique jour par jour.
    now = timezone.now()
    today = now.astimezone(LIBREVILLE_TZ).date()
    start = datetime.combine(today - timedelta(days=days - 1), time.min, tzinfo=LIBREVILLE_TZ)
    sold = Order.objects.filter(store=store, status__in=SOLD)
    current = sold.filter(created_at__gte=start)
    previous = sold.filter(created_at__gte=start - timedelta(days=days), created_at__lt=start)
    summary = _summary(current, previous)

    plan = store.get_current_plan()
    if not has(plan, 'advanced_stats'):
        return Response({'success': True, 'data': {
            'locked': True, 'days': days, 'summary': summary,
            'plan_name': plan.name if plan else 'Gratuit',
            'message': required_message('advanced_stats', plan),
        }})

    # Ventes jour par jour, heures et jours de la semaine (heure de Libreville).
    by_day = defaultdict(lambda: [0, ZERO])
    hours, weekdays = [0] * 24, [0] * 7
    for created, total in current.values_list('created_at', 'items_total'):
        local = created.astimezone(LIBREVILLE_TZ)
        by_day[local.date()][0] += 1
        by_day[local.date()][1] += total or ZERO
        hours[local.hour] += 1
        weekdays[local.weekday()] += 1
    daily = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        count, revenue = by_day.get(day, (0, ZERO))
        daily.append({'date': day.isoformat(), 'orders': count, 'revenue': _money(revenue)})

    line_total = ExpressionWrapper(F('unit_price') * F('quantity'), output_field=DecimalField(max_digits=14, decimal_places=2))
    items = OrderItem.objects.filter(order__in=current)
    top_products = [
        {'product_id': row['product_id'], 'name': row['product__name'], 'quantity': row['sold'],
         'revenue': _money(row['earned'])}
        for row in items.values('product_id', 'product__name')
        .annotate(sold=Sum('quantity'), earned=Sum(line_total)).order_by('-earned', '-sold')[:10]
    ]
    categories = [
        {'name': row['product__category__name'] or 'Sans catégorie', 'quantity': row['sold'],
         'revenue': _money(row['earned'])}
        for row in items.values('product__category__name')
        .annotate(sold=Sum('quantity'), earned=Sum(line_total)).order_by('-earned')[:8]
    ]

    per_client = list(current.values('client_id').annotate(n=Count('id')).values_list('n', flat=True))
    new_clients = (sold.values('client_id').annotate(first=Min('created_at'))
                   .filter(first__gte=start).count())
    sold_ids = items.values('product_id')
    slow = [
        {'product_id': p.id, 'name': p.name, 'stock': p.stock}
        for p in Product.objects.filter(store=store, is_available=True, stock__gt=0)
        .exclude(id__in=sold_ids).order_by('-stock')[:5]
    ]
    # Seules les commandes confirmées comptent : un panier jamais payé, annulé tout seul, n'est pas une annulation.
    placed = Order.objects.filter(store=store, created_at__gte=start, confirmed_at__isnull=False)
    placed_count = placed.count()
    cancelled = placed.filter(status__in=('cancelled', 'refunded')).count()

    best_hour = max(range(24), key=lambda h: hours[h]) if any(hours) else None
    best_day = max(range(7), key=lambda d: weekdays[d]) if any(weekdays) else None
    return Response({'success': True, 'data': {
        'locked': False,
        'days': days,
        'summary': summary,
        'daily': daily,
        'top_products': top_products,
        'categories': categories,
        'customers': {
            'unique': len(per_client),
            'returning': sum(1 for n in per_client if n >= 2),
            'new': new_clients,
        },
        'hours': hours,
        'weekdays': [{'day': WEEKDAYS[i], 'orders': weekdays[i]} for i in range(7)],
        'best_hour': best_hour,
        'best_weekday': WEEKDAYS[best_day] if best_day is not None else None,
        'slow_products': slow,
        'cancellation_rate': round(cancelled * 100 / placed_count) if placed_count else 0,
    }})
