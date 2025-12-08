import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from users.models import User

phone = '+241970000001'
password = 'TestPass123'

u = User.objects.filter(phone=phone).first()
if u:
    print('SKIPPED - user exists')
else:
    User.objects.create_user(phone=phone, password=password, email='test@example.com')
    print('CREATED')
