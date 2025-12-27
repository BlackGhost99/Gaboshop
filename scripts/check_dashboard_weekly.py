import os, sys
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','gaboshop.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
User=get_user_model()
user=User.objects.filter(is_superuser=True).first() or User.objects.first()
if not user:
    print('NO_USER')
else:
    client=APIClient(); client.force_authenticate(user=user)
    resp=client.get('/api/v1/dashboard/store/')
    print('status', resp.status_code)
    data = resp.data.get('data', {})
    print('keys:', list(data.keys()))
    print('weekly_revenue sample:', data.get('weekly_revenue')[:3] if data.get('weekly_revenue') else None)
