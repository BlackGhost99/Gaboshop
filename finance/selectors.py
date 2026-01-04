"""
Finance selectors - Query logic and aggregations
"""
from orders.models import Order, OrderItem
from .models import Expense
from django.db.models import Sum, Count, Q, F, DecimalField, ExpressionWrapper
from django.db.models.functions import Coalesce
from decimal import Decimal


def get_sales_summary(store, date_from=None, date_to=None, **filters):
    """Agrégats des ventes"""
    orders = Order.objects.filter(store=store)
    
    # Appliquer limite historique
    from .services import apply_history_limit
    orders = apply_history_limit(orders, store, 'created_at')
    
    if date_from:
        orders = orders.filter(created_at__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__lte=date_to)
    
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
        total_service_fees=Coalesce(Sum('service_fee'), Decimal('0')),
        total_delivery_fees=Coalesce(Sum('delivery_fee'), Decimal('0')),
        payment_fees=Coalesce(Sum('payment_fees'), Decimal('0')),
        orders_count=Count('id'),
    )
    
    # Net reçu = gross - commission - service_fees
    aggregates['net_received'] = (
        aggregates['gross_sales'] - 
        aggregates['total_commission'] - 
        aggregates['total_service_fees']
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
        orders = orders.filter(created_at__lte=date_to)
    
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
