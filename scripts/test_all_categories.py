import os, sys
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
import django
django.setup()
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
User = get_user_model()
user = User.objects.filter(is_superuser=True).first() or User.objects.first()
client = APIClient()
if user is None:
    print('NO_USER')
else:
    client.force_authenticate(user=user)
    resp = client.get('/api/v1/products/categories/')
    print('status', resp.status_code)
    try:
        print(resp.data)
    except Exception:
        print(resp.content)
