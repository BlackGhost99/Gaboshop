import os, sys
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','gaboshop.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from stores.models import Store
User=get_user_model()
user=User.objects.filter(is_superuser=True).first() or User.objects.first()
if not user:
    print('NO_USER')
else:
    client=APIClient(); client.force_authenticate(user=user)
    s=Store.objects.first()
    if not s:
        print('NO_STORE')
    else:
        print('Before offers_delivery=', s.offers_delivery)
        resp=client.patch(f'/api/v1/stores/{s.id}/update/', {'offers_delivery':'true'})
        print('status', resp.status_code)
        try:
            print(resp.data)
        except Exception:
            print(resp.content)
        s.refresh_from_db()
        print('After offers_delivery=', s.offers_delivery)
