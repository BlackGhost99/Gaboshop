"""Assign sensible model permissions to project groups.

Groups expected (create them in admin if not present):
- Admin
- Gerand
- Livreur
- Client

This script is idempotent: it will create groups if missing and assign permissions.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType

def get_perm(codename):
    try:
        return Permission.objects.get(codename=codename)
    except Permission.DoesNotExist:
        return None

def assign_perms_to_group(group_name, perm_codenames):
    group, created = Group.objects.get_or_create(name=group_name)
    perms = []
    for codename in perm_codenames:
        p = get_perm(codename)
        if p:
            perms.append(p)
        else:
            print(f"Warning: permission '{codename}' not found")
    if perms:
        group.permissions.add(*perms)
    return group

def main():
    # Map of groups to permission codenames
    mapping = {
        # Admin: full access to everything
        'Admin': [p.codename for p in Permission.objects.all()],

        # Gerand (store manager): manage store products and view/change orders for their store
        'Gerand': [
            'add_product', 'change_product', 'delete_product', 'view_product',
            'view_store', 'change_store',
            'view_order', 'change_order',
            'view_payment',
        ],

        # Livreur (delivery agent): view and update deliveries and change order status when delivering
        'Livreur': [
            'view_delivery', 'change_delivery',
            'view_order', 'change_order',
        ],

        # Client: create orders and view their own orders
        'Client': [
            'add_order', 'view_order',
        ],
    }

    results = {}
    for group_name, perms in mapping.items():
        grp = assign_perms_to_group(group_name, perms)
        results[group_name] = grp.permissions.count()

    print('Assignment complete. Permission counts per group:')
    for k, v in results.items():
        print(f" - {k}: {v}")

if __name__ == '__main__':
    main()
