#!/usr/bin/env python
"""Test script to check admin loading and errors."""
import os
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

import django
django.setup()

from django.contrib.admin import site
print("✓ Admin site loaded successfully")

# Try to access the admin URLs
try:
    urls = site.urls
    print(f"✓ Admin URLs: {urls}")
except Exception as e:
    print(f"✗ Error loading admin URLs: {e}")
    import traceback
    traceback.print_exc()

# Check if any apps are registered
print(f"✓ Registered apps: {len(site._registry)} models registered")
for model, admin_class in site._registry.items():
    print(f"  - {model.__name__}")
