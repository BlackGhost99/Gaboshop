import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()
settings.ALLOWED_HOSTS += ['testserver']

from rest_framework.test import APIClient
from users.models import User

def test_endpoint(client, url, name):
    print(f"Testing {name} ({url})...")
    try:
        response = client.get(url)
        if response.status_code == 200:
            print(f"  [OK] {name}")
        else:
            print(f"  [FAIL] {name} - Status: {response.status_code}")
            print(f"  Error: {response.data}")
    except Exception as e:
        print(f"  [CRASH] {name} - {e}")

def test_all():
    print("Testing ALL Admin Endpoints...")
    client = APIClient()
    
    user = User.objects.filter(user_type='admin').first()
    if not user:
        user = User.objects.create_user(phone='00000000', password='password', user_type='admin')
    
    client.force_authenticate(user=user)
    
    endpoints = [
        ('/api/v1/admin/summary/', 'Admin Summary'),
        ('/api/v1/admin/users/', 'Admin Users'),
        ('/api/v1/admin/orders/', 'Admin Orders'),
        ('/api/v1/admin/financials/', 'Admin Financials'),
        ('/api/v1/admin/store-categories/', 'Store Categories'),
        ('/api/v1/admin/product-categories/', 'Product Categories'),
        ('/api/v1/admin/payments/', 'Admin Payments'),
        ('/api/v1/admin/deliveries/', 'Admin Deliveries'),
        ('/api/v1/admin/stores/', 'Admin Stores'),
        ('/api/v1/settings/', 'System Settings'),
        ('/api/v1/finance/dashboard/', 'Finance Dashboard'),
        ('/api/v1/finance/transactions/', 'Transactions'),
        ('/api/v1/finance/commissions/', 'Commissions'),
        ('/api/v1/finance/delivery-payouts/', 'Delivery Payouts'),
        ('/api/v1/finance/subscriptions/', 'Subscriptions'),
        ('/api/v1/finance/sponsored-products/', 'Sponsored Products'),
        ('/api/v1/finance/revenue-breakdown/', 'Revenue Breakdown'),
    ]
    
    for url, name in endpoints:
        test_endpoint(client, url, name)

if __name__ == '__main__':
    test_all()
