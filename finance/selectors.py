"""
Finance selectors - Query logic and aggregations
"""
from orders.models import Order, OrderItem
from .models import Expense
from django.db.models import Sum, Count, Q, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from datetime import date, datetime, time
from decimal import Decimal

from django.utils import timezone


def inclusive_end(date_to):
    """Un jour seul (« 2026-10-17 ») couvre toute la journée : sinon les ventes du dernier jour choisi disparaissent."""
    text = str(date_to or '').strip()
    if len(text) != 10:
        return date_to
    try:
        day = date.fromisoformat(text)
    except ValueError:
        return date_to
    return timezone.make_aware(datetime.combine(day, time.max))


def get_sales_summary(store, date_from=None, date_to=None, **filters):
    """Agrégats des ventes"""
    orders = Order.objects.filter(store=store)
    
    # Appliquer limite historique
    from .services import apply_history_limit
    orders = apply_history_limit(orders, store, 'created_at')
    
    if date_from:
        orders = orders.filter(created_at__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__lte=inclusive_end(date_to))
    
    # Filtres additionnels
    if filters.get('status'):
        orders = orders.filter(status=filters['status'])
    if filters.get('payment_method'):
        orders = orders.filter(payment_method=filters['payment_method'])
    if filters.get('is_b2b') is not None:
        orders = orders.filter(is_b2b=filters['is_b2b'])
    
    aggregates = orders.aggregate(
        gross_sales=Coalesce(Sum('items_total'), Decimal('0')),
        total_commission=Coalesce(Sum('commission_amount'), Decimal('0')),
        total_delivery_fees=Coalesce(Sum('delivery_fee'), Decimal('0')),
        payment_fees=Coalesce(Sum('payment_fees'), Decimal('0')),
        orders_count=Count('id'),
    )
    
    # Net recu = gross - commission
    aggregates['net_received'] = (
        aggregates['gross_sales'] - 
        aggregates['total_commission']
    )
    
    # Refunds
    refunded = orders.filter(status__in=['refunded', 'partial_refund']).aggregate(
        refunds_total=Coalesce(Sum('total_amount'), Decimal('0'))
    )
    aggregates['refunds_total'] = refunded['refunds_total']
    
    return aggregates


def get_expenses_summary(store, date_from=None, date_to=None, **filters):
    """Agrégats des dépenses"""
    expenses = Expense.objects.filter(store=store)
    
    # Appliquer limite historique
    from .services import apply_history_limit
    expenses = apply_history_limit(expenses, store, 'expense_date')
    
    if date_from:
        expenses = expenses.filter(expense_date__gte=date_from)
    if date_to:
        expenses = expenses.filter(expense_date__lte=date_to)
    
    if filters.get('expense_type'):
        expenses = expenses.filter(expense_type=filters['expense_type'])
    
    aggregates = expenses.aggregate(
        expenses_total=Coalesce(Sum('amount'), Decimal('0')),
        expenses_count=Count('id'),
    )
    
    return aggregates


def get_top_categories(store, date_from=None, date_to=None, limit=5):
    """Retourne les top catégories par ventes (pour Pro/Business)"""
    orders = Order.objects.filter(store=store, status='delivered')
    
    from .services import apply_history_limit
    orders = apply_history_limit(orders, store, 'created_at')
    
    if date_from:
        orders = orders.filter(created_at__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__lte=inclusive_end(date_to))
    
    # Agrégation par catégorie
    order_items = OrderItem.objects.filter(order__in=orders).select_related('product__category')

    line_total_expr = ExpressionWrapper(
        F('quantity') * F('unit_price'),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    top_categories = order_items.values(
        'product__category__name'
    ).annotate(
        total_sales=Coalesce(Sum(line_total_expr), Decimal('0')),
        items_sold=Coalesce(Sum('quantity'), 0)
    ).order_by('-total_sales')[:limit]
    
    return list(top_categories)


def get_category_detailed_report(store, date_from=None, date_to=None):
    """
    Rapport détaillé par catégorie : pour chacune, ses ventes et les commandes livrées qui les composent.
    Réservé aux forfaits qui incluent « detailed_finance » (can_view_finance_detailed) ; le contrôle est fait par la vue.

    Retourne une liste triée par ventes décroissantes :
    [{category_id, category_name, total_sales, items_sold, orders_count,
      orders: [{order_id, order_number, created_at, buyer_name, is_b2b, sales, items_sold}]}]
    """
    orders = Order.objects.filter(store=store, status='delivered')

    from .services import apply_history_limit
    orders = apply_history_limit(orders, store, 'created_at')

    if date_from:
        orders = orders.filter(created_at__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__lte=inclusive_end(date_to))

    line_total_expr = ExpressionWrapper(
        F('quantity') * F('unit_price'),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )

    lines = OrderItem.objects.filter(order__in=orders).values(
        'product__category__id',
        'product__category__name',
        'order__id',
        'order__order_number',
        'order__created_at',
        'order__is_b2b',
        'order__source_store__name',
        'order__client__first_name',
        'order__client__last_name',
    ).annotate(
        category_sales=Coalesce(Sum(line_total_expr), Decimal('0')),
        items_sold=Coalesce(Sum('quantity'), 0),
    ).order_by('-order__created_at')

    categories = {}
    for line in lines:
        key = line['product__category__id']
        category = categories.setdefault(key, {
            'category_id': key,
            'category_name': line['product__category__name'] or 'Sans catégorie',
            'total_sales': Decimal('0'),
            'items_sold': 0,
            'orders': [],
        })
        if line['order__is_b2b'] and line['order__source_store__name']:
            buyer = line['order__source_store__name']
        else:
            buyer = f"{line['order__client__first_name'] or ''} {line['order__client__last_name'] or ''}".strip() or 'Client'
        category['total_sales'] += line['category_sales']
        category['items_sold'] += line['items_sold']
        category['orders'].append({
            'order_id': line['order__id'],
            'order_number': line['order__order_number'],
            'created_at': line['order__created_at'],
            'buyer_name': buyer,
            'is_b2b': bool(line['order__is_b2b']),
            'sales': line['category_sales'],
            'items_sold': line['items_sold'],
        })

    report = sorted(categories.values(), key=lambda category: category['total_sales'], reverse=True)
    for category in report:
        category['orders_count'] = len(category['orders'])
    return report
