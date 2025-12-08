import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from api.v1.admin import AdminSummaryView
from rest_framework.test import APIRequestFactory

def test_admin_summary():
    print("Testing AdminSummaryView...")
    factory = APIRequestFactory()
    request = factory.get('/api/v1/admin/summary/')
    
    # Mock user
    from users.models import User
    try:
        user = User.objects.filter(user_type='admin').first()
        if not user:
            print("No admin user found, creating one...")
            user = User.objects.create_user(phone='00000000', password='password', user_type='admin')
    except Exception as e:
        print(f"Error getting/creating user: {e}")
        return

    request.user = user
    
    view = AdminSummaryView()
    try:
        response = view.get(request)
        print(f"Response Status: {response.status_code}")
        if response.status_code == 200:
            print("Success! Data keys:", response.data.get('data', {}).keys())
        else:
            print("Failed response:", response.data)
    except Exception as e:
        print(f"CRASHED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_admin_summary()
