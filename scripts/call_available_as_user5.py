from rest_framework.test import APIRequestFactory
from django.contrib.auth import get_user_model
from api.v1.delivery import AvailableDeliveriesView

User = get_user_model()
user = User.objects.filter(id=5).first()
print('USER', user and user.id, user and user.phone, 'city', user and user.city)

factory = APIRequestFactory()
request = factory.get('/api/v1/dashboard/delivery/available/')
request.user = user
view = AvailableDeliveriesView.as_view()
response = view(request)
print('STATUS', response.status_code)
try:
    print('DATA', response.data)
except Exception as e:
    print('NO DATA', e)
