from delivery.models import Delivery
from users.models import User

print('WAITING DELIVERIES:')
qs = Delivery.objects.filter(status='waiting')
for d in qs:
    print('DELIVERY', d.id, 'order', d.order.order_number, 'city', d.city, 'order_status', d.order.status)

print('\nDELIVERY AGENTS AND VISIBLE DELIVERIES:')
agents = User.objects.filter(user_type='delivery_agent')
for a in agents:
    city = a.city
    is_agent = a.is_delivery_agent()
    print('\nAGENT', a.id, a.phone, 'city', city, 'is_delivery_agent', is_agent)
    # Simulate AvailableDeliveriesView.get_queryset
    visible = Delivery.objects.filter(status='waiting')
    if hasattr(a, 'city') and a.city:
        visible = visible.filter(city=a.city)
    visible = visible.filter(order__status__in=['ready','paid','confirmed'])
    print('VISIBLE_COUNT', visible.count())
    for v in visible:
        print(' ->', v.id, v.order.order_number, v.city, v.order.status)
