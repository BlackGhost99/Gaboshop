from django.utils import timezone
from orders.models import Order
from delivery.models import Delivery
from payments.models import Payment
from users.models import User

ORDER_NUMBER = 'CMD08424233'

o = Order.objects.filter(order_number=ORDER_NUMBER).select_related('store','client').first()
if not o:
    print('NO_ORDER')
else:
    print('ORDER', o.id, o.order_number, 'status', o.status, 'store_id', o.store_id, 'city', o.city, 'created_at', o.created_at)
    try:
        p = o.payment
        print('PAYMENT', p.id, p.status, 'amount', p.amount, 'completed_at', p.completed_at)
    except Exception:
        print('NO_PAYMENT')
    d = Delivery.objects.filter(order=o).select_related('delivery_agent').first()
    if not d:
        print('NO_DELIVERY')
    else:
        print('DELIVERY', d.id, 'status', d.status, 'agent_id', getattr(d.delivery_agent,'id',None), 'assigned_at', d.assigned_at)

    agents = User.objects.filter(user_type='delivery_agent', is_available=True, city=o.city)
    print('AVAILABLE_AGENTS_IN_CITY', agents.count())
    for a in agents[:20]:
        print('AGENT', a.id, a.phone, 'is_available', a.is_available, 'city', a.city, 'pos_lat', getattr(a,'position_lat',None), 'pos_lng', getattr(a,'position_lng',None))

    # If delivery exists and is waiting and unassigned, print detail
    if d and d.status in ('waiting','created') and not getattr(d,'delivery_agent',None):
        print('DELIVERY_WAITING_UNASSIGNED')

    # show commission/commission object if exists
    try:
        com = o.commission
        print('COMMISSION', com.id, com.commission_amount, com.commission_rate, 'settled', com.is_settled)
    except Exception:
        print('NO_COMMISSION')
