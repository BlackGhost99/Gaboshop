from django.utils import timezone
from orders.models import Order
from payments.models import Payment

order = Order.objects.filter(status__in=['pending_payment','created']).exclude(payment__isnull=False).first()
if not order:
    order = Order.objects.filter(status__in=['ready','confirmed']).exclude(payment__isnull=False).first()

if not order:
    print('NO_ORDER')
else:
    print('ORDER', order.id, order.order_number, order.status)
    amt = order.total_amount if order.total_amount else order.items_total
    p = Payment.objects.create(order=order, payment_method='cash', status='success', amount=amt, client_phone=(order.client.phone if order.client else ''), completed_at=timezone.now())
    print('CREATED_PAYMENT', p.id)
    import time
    time.sleep(6)
    try:
        from delivery.models import Delivery
        d = Delivery.objects.get(order=order)
        print('DELIVERY', d.id, d.status, 'agent_id', getattr(d.delivery_agent, 'id', None), 'assigned_at', d.assigned_at)
    except Exception as e:
        print('DELIVERY_ERROR', e)
