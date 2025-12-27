import os
import sys
# ensure project root is importable so `gaboshop.settings` can be found
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
import django
django.setup()

from api.v1.products import DEFAULT_CATEGORY_TEMPLATES
from stores.models import StoreCategory
from products.models import ProductCategory

created = 0
skipped = 0
details = []

for sc in StoreCategory.objects.all():
    qs = ProductCategory.objects.filter(store_category=sc)
    if qs.exists():
        skipped += 1
        details.append(f'SKIP {sc.id} {sc.name} ({qs.count()} existing)')
    else:
        names = DEFAULT_CATEGORY_TEMPLATES.get(sc.name, [])
        if not names:
            # No predefined templates for this StoreCategory: create a generic fallback
            fallback_name = 'Autres'
            ProductCategory.objects.create(name=fallback_name, description='', order=0, store_category=sc)
            created += 1
            details.append(f'CREATED fallback 1 for {sc.id} {sc.name}')
            continue
        for i, n in enumerate(names):
            ProductCategory.objects.create(name=n, description='', order=i, store_category=sc)
            created += 1
        details.append(f'CREATED {len(names)} for {sc.id} {sc.name}')

print('Created=', created, 'Skipped store-categories=', skipped)
for d in details:
    print(d)
