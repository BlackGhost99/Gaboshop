#!/usr/bin/env python
"""Test script to check admin login endpoint."""
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')

import django
django.setup()

from django.test import Client

try:
    client = Client()
    
    # Test admin index
    print("Testing /admin/ ...") 
    response = client.get('/admin/')
    print(f"✓ Admin index status: {response.status_code}")
    
    # Test admin login
    print("\nTesting /admin/login/ ...")
    response2 = client.get('/admin/login/')
    print(f"✓ Admin login status: {response2.status_code}")
    
    # If there's a 500, try to get the error
    if response2.status_code >= 500:
        print("✗ Got 500 error on login")
        print(f"Response content length: {len(response2.content)}")
        if b'Traceback' in response2.content:
            print("✓ Traceback found in response")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
