import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from users.models import User

PHONE_PATTERN = '01010101'
NEW_PASSWORD = 'mot2passe'

matches = User.objects.filter(phone__icontains=PHONE_PATTERN)
if not matches.exists():
    print('No user found matching phone pattern:', PHONE_PATTERN)
else:
    for u in matches:
        u.set_password(NEW_PASSWORD)
        u.save()
        print(f"Updated user id={u.id}, phone={u.phone}")
