import os, sys
sys.path.insert(0, os.path.abspath('.'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
import django
django.setup()
from products.models import ProductCategory
print('Total categories:', ProductCategory.objects.count())
for c in ProductCategory.objects.all()[:5]:
    print(f'{c.id}: {c.name} (store_cat: {c.store_category.name if c.store_category else None})')