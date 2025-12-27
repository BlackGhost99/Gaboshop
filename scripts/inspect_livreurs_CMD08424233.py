from orders.models import Order
from users.models import LivreurProfile

ORDER_NUMBER = 'CMD08424233'
o = Order.objects.filter(order_number=ORDER_NUMBER).first()
if not o:
    print('NO_ORDER')
else:
    city = o.city
    print('ORDER_CITY', city)
    profiles = LivreurProfile.objects.filter(user__city=city)
    print('LIVREUR_PROFILES_COUNT', profiles.count())
    for p in profiles:
        print('PROFILE', p.id, 'user_id', p.user.id, 'phone', p.user.phone, 'disponible', p.disponible, 'documents_verifies', p.documents_verifies, 'pos_lat', p.position_lat, 'pos_lng', p.position_lng, 'last_update', p.last_position_update)
