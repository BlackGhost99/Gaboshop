"""
Seed default CategoryCommission records for existing StoreCategory entries.
"""
import os
import django

import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from stores.models import StoreCategory
from payments.models import CategoryCommission

# Default mapping by category name (case-insensitive substring matching)
DEFAULT_RATES = [
    ('aliment', 0.00),  # alimentation / food -> 0%
    ('mode', 10.00),
    ('textile', 10.00),
    ('électron', 8.00),
    ('electron', 8.00),
    ('cosmé', 10.00),
    ('cosme', 10.00),
    ('service', 12.00),
]

created = 0
updated = 0
skipped = 0

for sc in StoreCategory.objects.all():
    name = sc.name.lower()
    # find a matching default
    rate = None
    for key, r in DEFAULT_RATES:
        if key in name:
            rate = r
            break
    if rate is None:
        rate = 8.00  # default base

    obj, is_created = CategoryCommission.objects.get_or_create(
        store_category=sc,
        defaults={'base_rate': rate}
    )
    if is_created:
        print(f"CREATED commission for {sc.name}: {rate}%")
        created += 1
    else:
        # update only if different
        if float(obj.base_rate) != float(rate):
            obj.base_rate = rate
            obj.save()
            print(f"UPDATED commission for {sc.name} -> {rate}%")
            updated += 1
        else:
            print(f"SKIP {sc.name} (exists {obj.base_rate}%)")
            skipped += 1

print(f"\nSummary: created={created} updated={updated} skipped={skipped}")
