import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()
settings.ALLOWED_HOSTS += ['testserver']

from rest_framework.test import APIClient
from users.models import User

def test_products_list():
    print("Testing ProductsListView with APIClient...")
    client = APIClient()
    
    user = User.objects.filter(user_type='admin').first()
    if not user:
        user = User.objects.create_user(phone='00000000', password='password', user_type='admin')
    
    client.force_authenticate(user=user)
    
    try:
        response = client.get('/api/v1/admin/products/list/')
        print(f"Response Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Success! Count: {data.get('count')}")
            if data.get('data'):
                print("First product sample:", data['data'][0])
        else:
            print("Failed response:", response.data)
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_products_list()
