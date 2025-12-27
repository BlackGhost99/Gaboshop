import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
django.setup()

from users.models import User
from stores.models import StoreCategory, Store

def run():
    phone = '077700001'
    password = 'demoPass123'
    if not User.objects.filter(phone=phone).exists():
        user = User.objects.create_user(phone=phone, password=password, user_type='store_manager')
        print('Created user', phone)
    else:
        user = User.objects.get(phone=phone)
        print('User exists', phone)

    cat, _ = StoreCategory.objects.get_or_create(name='Démo')

    if not Store.objects.filter(manager=user).exists():
        store = Store.objects.create(
            name='Demo Store',
            category=cat,
            manager=user,
            phone='077700002',
            address='Demo Address',
            zone='Demo Zone',
        )
        print('Created store Demo Store')
    else:
        store = Store.objects.get(manager=user)
        print('Store exists for user')

    print('LOGIN CREDENTIALS:')
    print('phone:', phone)
    print('password:', password)

if __name__ == '__main__':
    run()
