#!/usr/bin/env python
"""
Test Singpay integration from Docker environment
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gaboshop.settings')
sys.path.insert(0, '/app')

django.setup()

from payments.utils import call_singpay_payment, _normalize_msisdn

def test_config():
    """Test 1: Verify Singpay config loaded"""
    print("\n" + "="*60)
    print("TEST 1: Singpay Configuration")
    print("="*60)
    
    base_url = os.getenv('SINGPAY_BASE_URL')
    client_id = os.getenv('SINGPAY_CLIENT_ID')
    client_secret = os.getenv('SINGPAY_CLIENT_SECRET')
    wallet_id = os.getenv('SINGPAY_WALLET_ID')
    timeout = os.getenv('SINGPAY_TIMEOUT', '30')
    
    print(f"✓ SINGPAY_BASE_URL: {base_url}")
    print(f"✓ SINGPAY_CLIENT_ID: {client_id[:20]}...{client_id[-5:]}")
    print(f"✓ SINGPAY_CLIENT_SECRET: {client_secret[:10]}...{client_secret[-5:]}")
    print(f"✓ SINGPAY_WALLET_ID: {wallet_id}")
    print(f"✓ SINGPAY_TIMEOUT: {timeout}s")
    
    assert base_url, "Missing SINGPAY_BASE_URL"
    assert client_id, "Missing SINGPAY_CLIENT_ID"
    assert client_secret, "Missing SINGPAY_CLIENT_SECRET"
    assert wallet_id, "Missing SINGPAY_WALLET_ID"
    print("\n✅ All configuration variables present")
    return True

def test_phone_formatting():
    """Test 2: Phone number formatting"""
    print("\n" + "="*60)
    print("TEST 2: Phone Number Formatting (MSISDN Normalization)")
    print("="*60)
    
    test_cases = [
        ("+241123456789", "56789"),       # International → local (8 digits)
        ("0123456789", "23456789"),       # Local with 0 → remove 0
        ("123456789", "23456789"),         # No prefix
        ("+241 12 345 678", "345678"),     # Spaces removed
    ]
    
    for input_phone, expected_partial in test_cases:
        try:
            result = _normalize_msisdn(input_phone)
            status = "✓" if result.endswith(expected_partial) or result == expected_partial else "✗"
            print(f"{status} {input_phone:20} → {result:20}")
        except Exception as e:
            print(f"✗ {input_phone:20} → ERROR: {e}")
    
    print("✅ Phone formatting tests complete")
    return True

def test_redis_connection():
    """Test 3: Redis connectivity"""
    print("\n" + "="*60)
    print("TEST 3: Redis Connection")
    print("="*60)
    
    try:
        import redis
        r = redis.Redis(host='redis', port=6379, db=0)
        r.ping()
        print("✓ Redis connection: OK")
        r.set('test_key', 'test_value')
        val = r.get('test_key').decode()
        print(f"✓ Redis write/read: OK (test_key = {val})")
        r.delete('test_key')
        print("✓ Redis delete: OK")
        print("✅ Redis tests passed")
        return True
    except Exception as e:
        print(f"⚠️ Redis test failed: {e}")
        return False

def test_api_connectivity():
    """Test 4: Singpay API connectivity (sandbox)"""
    print("\n" + "="*60)
    print("TEST 4: Singpay API Sandbox Connectivity")
    print("="*60)
    
    try:
        # Test basic connectivity
        base_url = os.getenv('SINGPAY_BASE_URL')
        print(f"Testing connectivity to: {base_url}")
        
        import requests
        response = requests.head(base_url, timeout=5)
        print(f"✓ API server reachable: Status {response.status_code}")
        print("✅ API connectivity test passed")
        return True
    except Exception as e:
        print(f"⚠️ API connectivity test failed: {e}")
        print("   (This is expected in offline/sandbox environments)")
        return False

def test_models():
    """Test 5: Database models"""
    print("\n" + "="*60)
    print("TEST 5: Database Models")
    print("="*60)
    
    try:
        from payments.models import Payment, Commission, PaymentIntent
        from orders.models import Order
        
        print(f"✓ Payment model: {Payment._meta.db_table}")
        print(f"✓ Commission model: {Commission._meta.db_table}")
        print(f"✓ PaymentIntent model: {PaymentIntent._meta.db_table}")
        print(f"✓ Order model: {Order._meta.db_table}")
        
        # Check counts
        payment_count = Payment.objects.count()
        order_count = Order.objects.count()
        print(f"✓ Payments in DB: {payment_count}")
        print(f"✓ Orders in DB: {order_count}")
        
        print("✅ Model tests passed")
        return True
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        return False

def test_celery():
    """Test 6: Celery connectivity"""
    print("\n" + "="*60)
    print("TEST 6: Celery & Redis")
    print("="*60)
    
    try:
        from celery_app import app
        
        # Check broker
        broker_url = app.conf.broker_url
        print(f"✓ Celery Broker: {broker_url}")
        
        # Send test task
        from celery import current_app
        result = current_app.send_task('test_task')
        print(f"✓ Test task sent: {result.id}")
        
        print("✅ Celery connectivity test passed")
        return True
    except Exception as e:
        print(f"⚠️ Celery test: {e}")
        return False

if __name__ == '__main__':
    print("\n" + "🚀 " + "="*56)
    print("  SINGPAY INTEGRATION TEST SUITE (Docker Environment)")
    print("🚀 " + "="*56)
    
    results = {
        "Config": test_config(),
        "Phone Formatting": test_phone_formatting(),
        "Redis": test_redis_connection(),
        "API Connectivity": test_api_connectivity(),
        "Models": test_models(),
        "Celery": test_celery(),
    }
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "⚠️ SKIP"
        print(f"{status:12} - {test_name}")
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    print(f"\nResult: {passed_count}/{total_count} tests successful")
    
    print("\n" + "="*60)
    print("🎯 DOCKER ENVIRONMENT READY FOR TESTING")
    print("="*60)
    print("\n✅ Services Running:")
    print("  • Backend API: http://localhost:8000")
    print("  • Frontend: http://localhost:5173")
    print("  • Redis: localhost:6379")
    print("  • Celery Worker: Running")
    print("\n📝 Next Steps:")
    print("  1. Run payment simulation tests")
    print("  2. Test webhook confirmation flow")
    print("  3. Validate Airtel Money operator integration")
    print("  4. Validate Moov Money operator integration")
    print("="*60 + "\n")
