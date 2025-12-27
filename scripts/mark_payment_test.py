from django.utils import timezone
from payments.models import Payment
from delivery.models import Delivery
from time import sleep

p = Payment.objects.filter(status__in=['pending','processing','failed','cancelled']).exclude(order__status='paid').first()
if not p:
    print('NO_PAYMENT')
else:
    print('FOUND', p.id, p.order.order_number, 'order_status', p.order.status)
    p.status = 'success'
    p.completed_at = timezone.now()
    p.save()
    print('UPDATED', p.id)
    print('Waiting 6s for celery task...')
    sleep(6)
    try:
        d = Delivery.objects.get(order=p.order)
        print('DELIVERY', d.id, d.status, 'agent_id', getattr(d.delivery_agent, 'id', None), 'assigned_at', d.assigned_at)
    except Delivery.DoesNotExist:
        print('NO_DELIVERY_RECORD')
    except Exception as e:
        print('DELIVERY_ERROR', e)
