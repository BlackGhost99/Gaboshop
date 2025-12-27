from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
user = User.objects.filter(id=5).first()
if not user:
    print('NO_USER')
else:
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    print('ACCESS', access)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='Bearer ' + access)
    resp = client.get('/api/v1/dashboard/delivery/available/')
    print('STATUS', resp.status_code)
    print('DATA', resp.json())
