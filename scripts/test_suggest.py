import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE','gaboshop.settings')
import django
django.setup()
from stores.models import Store
from api.v1.products import get_suggested_categories_for_store
s = Store.objects.filter(is_active=True).first()
print('first store id:', s.id if s else None)
print('store category:', s.category.name if s and s.category else None)
print('suggestions:', get_suggested_categories_for_store(s))
