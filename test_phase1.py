#!/usr/bin/env python
"""
Phase 1 Test Script - Backend Testing
Tests the anti-fraud validation implementation

Usage:
    python test_phase1.py
"""

import os
import sys
import django
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from orders.models import Order
from delivery.models import Delivery
from stores.models import Store
from core.models import AuditLog

User = get_user_model()

# ANSI Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text:^70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.ENDC}\n")

def print_test(name, passed, message=""):
    icon = f"{Colors.GREEN}✓{Colors.ENDC}" if passed else f"{Colors.RED}✗{Colors.ENDC}"
    status = f"{Colors.GREEN}PASS{Colors.ENDC}" if passed else f"{Colors.RED}FAIL{Colors.ENDC}"
    print(f"{icon} {name:<50} {status}", end="")
    if message:
        print(f" - {Colors.YELLOW}{message}{Colors.ENDC}", end="")
    print()

def setup_test_data():
    """Create test data"""
    print(f"{Colors.BLUE}Setting up test data...{Colors.ENDC}")
    
    # Clean up old data
    AuditLog.objects.all().delete()
    Delivery.objects.all().delete()
    Order.objects.all().delete()
    
    # Create store manager
    manager = User.objects.filter(email='manager@test.com').first()
    if not manager:
        manager = User.objects.create_user(
            email='manager@test.com',
            password='test123',
            user_type='store_manager',
            first_name='Manager',
            last_name='Test'
        )
    
    # Create delivery agent
    driver = User.objects.filter(email='driver@test.com').first()
    if not driver:
        driver = User.objects.create_user(
            email='driver@test.com',
            password='test123',
            user_type='delivery_agent',
            first_name='Driver',
            last_name='Test'
        )
    
    # Create store
    store = Store.objects.create(
        name='Test Store',
        manager=manager,
        city='Paris'
    )
    
    # Create order
    order = Order.objects.create(
        store=store,
        status='ready',
        total_price=100.00
    )
    
    # Create delivery
    delivery = Delivery.objects.create(
        order=order,
        delivery_agent=driver,
        status='pending'
    )
    
    print(f"  {Colors.GREEN}✓{Colors.ENDC} Manager created: {manager.email}")
    print(f"  {Colors.GREEN}✓{Colors.ENDC} Driver created: {driver.email}")
    print(f"  {Colors.GREEN}✓{Colors.ENDC} Order created: #{order.id}")
    print(f"  {Colors.GREEN}✓{Colors.ENDC} Delivery created: #{delivery.id}\n")
    
    return manager, driver, store, order, delivery

def test_valid_transitions():
    """Test valid status transitions"""
    print_header("TEST 1: Valid Status Transitions")
    
    manager, driver, store, order, delivery = setup_test_data()
    client = Client()
    tests_passed = 0
    tests_total = 4
    
    # Test 1.1: Accept delivery
    print(f"{Colors.BLUE}1.1 Testing: Accept Delivery (pending → accepted){Colors.ENDC}")
    client.login(username='driver@test.com', password='test123')
    response = client.post(f'/api/v1/dashboard/delivery/{delivery.id}/accept/')
    
    passed = response.status_code == 200
    tests_passed += passed
    print_test("Accept delivery endpoint", passed, f"Status: {response.status_code}")
    
    if passed:
        delivery.refresh_from_db()
        print_test("Status updated to 'accepted'", delivery.status == 'accepted', 
                  f"Status: {delivery.status}")
        tests_passed += (delivery.status == 'accepted')
        tests_total += 1
    
    # Test 1.2: Start delivery
    print(f"\n{Colors.BLUE}1.2 Testing: Start Delivery (accepted → in_transit){Colors.ENDC}")
    response = client.post(f'/api/v1/dashboard/delivery/{delivery.id}/start/')
    
    passed = response.status_code == 200
    tests_passed += passed
    print_test("Start delivery endpoint", passed, f"Status: {response.status_code}")
    
    if passed:
        delivery.refresh_from_db()
        print_test("Status updated to 'in_transit'", delivery.status == 'in_transit',
                  f"Status: {delivery.status}")
        tests_passed += (delivery.status == 'in_transit')
        tests_total += 1
    
    # Test 1.3: Complete delivery
    print(f"\n{Colors.BLUE}1.3 Testing: Complete Delivery (in_transit → delivered){Colors.ENDC}")
    response = client.post(f'/api/v1/dashboard/delivery/{delivery.id}/complete/')
    
    passed = response.status_code == 200
    tests_passed += passed
    print_test("Complete delivery endpoint", passed, f"Status: {response.status_code}")
    
    if passed:
        delivery.refresh_from_db()
        print_test("Status updated to 'delivered'", delivery.status == 'delivered',
                  f"Status: {delivery.status}")
        tests_passed += (delivery.status == 'delivered')
        tests_total += 1
    
    return tests_passed, tests_total

def test_invalid_transitions():
    """Test invalid status transitions"""
    print_header("TEST 2: Invalid Status Transitions (Should Be Rejected)")
    
    manager, driver, store, order, delivery = setup_test_data()
    delivery.status = 'accepted'  # Set initial state
    delivery.save()
    
    client = Client()
    client.login(username='driver@test.com', password='test123')
    tests_passed = 0
    tests_total = 0
    
    # Test 2.1: Try to accept already accepted delivery
    print(f"{Colors.BLUE}2.1 Testing: Invalid - Accept Already Accepted Delivery{Colors.ENDC}")
    response = client.post(f'/api/v1/dashboard/delivery/{delivery.id}/accept/')
    
    passed = response.status_code in [400, 403]
    tests_passed += passed
    tests_total += 1
    print_test("Reject double acceptance", passed, f"Status: {response.status_code} (expected 400/403)")
    
    # Test 2.2: Verify audit log marks as suspicious
    print(f"\n{Colors.BLUE}2.2 Testing: Suspicious Activity Logging{Colors.ENDC}")
    suspicious_logs = AuditLog.objects.filter(
        object_type='delivery',
        object_id=delivery.id,
        is_suspicious=True
    )
    
    passed = suspicious_logs.exists()
    tests_passed += passed
    tests_total += 1
    print_test("Suspicious activity marked in audit log", passed, 
              f"Found {suspicious_logs.count()} suspicious logs")
    
    return tests_passed, tests_total

def test_unauthorized_access():
    """Test unauthorized access prevention"""
    print_header("TEST 3: Unauthorized Access Prevention")
    
    manager, driver, store, order, delivery = setup_test_data()
    
    # Create another driver
    hacker = User.objects.create_user(
        email='hacker@test.com',
        password='test123',
        user_type='delivery_agent',
        first_name='Hacker',
        last_name='Test'
    )
    
    client = Client()
    tests_passed = 0
    tests_total = 0
    
    # Test 3.1: Unauthorized driver tries to accept
    print(f"{Colors.BLUE}3.1 Testing: Unauthorized Driver Cannot Accept Others' Deliveries{Colors.ENDC}")
    client.login(username='hacker@test.com', password='test123')
    response = client.post(f'/api/v1/dashboard/delivery/{delivery.id}/accept/')
    
    passed = response.status_code == 403
    tests_passed += passed
    tests_total += 1
    print_test("Reject unauthorized access", passed, f"Status: {response.status_code} (expected 403)")
    
    # Test 3.2: Verify suspicious flag set
    print(f"\n{Colors.BLUE}3.2 Testing: Unauthorized Access Logged as Suspicious{Colors.ENDC}")
    suspicious_logs = AuditLog.objects.filter(
        user=hacker,
        object_type='delivery',
        is_suspicious=True
    )
    
    passed = suspicious_logs.exists()
    tests_passed += passed
    tests_total += 1
    print_test("Unauthorized attempt flagged as suspicious", passed,
              f"Found {suspicious_logs.count()} suspicious logs")
    
    # Test 3.3: Check IP address captured
    print(f"\n{Colors.BLUE}3.3 Testing: Security Details Captured{Colors.ENDC}")
    if suspicious_logs.exists():
        log = suspicious_logs.first()
        has_ip = log.ip_address is not None
        has_reason = log.reason != ''
        
        print_test("IP address captured", has_ip, f"IP: {log.ip_address}")
        tests_passed += has_ip
        tests_total += 1
        
        print_test("Reason recorded", has_reason, f"Reason: {log.reason}")
        tests_passed += has_reason
        tests_total += 1
    
    return tests_passed, tests_total

def test_audit_logging():
    """Test audit trail creation"""
    print_header("TEST 4: Audit Trail Logging")
    
    manager, driver, store, order, delivery = setup_test_data()
    initial_log_count = AuditLog.objects.count()
    
    client = Client()
    client.login(username='driver@test.com', password='test123')
    tests_passed = 0
    tests_total = 0
    
    # Perform action
    print(f"{Colors.BLUE}4.1 Testing: Audit Log Creation on Status Change{Colors.ENDC}")
    response = client.post(f'/api/v1/dashboard/delivery/{delivery.id}/accept/')
    
    new_log_count = AuditLog.objects.count()
    log_created = new_log_count > initial_log_count
    tests_passed += log_created
    tests_total += 1
    print_test("Audit log created on status change", log_created,
              f"Logs: {initial_log_count} → {new_log_count}")
    
    # Test 4.2: Check log details
    print(f"\n{Colors.BLUE}4.2 Testing: Audit Log Details{Colors.ENDC}")
    log = AuditLog.objects.filter(object_type='delivery', object_id=delivery.id).first()
    
    if log:
        # Check old value
        has_old = log.old_value == 'pending'
        print_test("Old status recorded", has_old, f"Old: {log.old_value}")
        tests_passed += has_old
        tests_total += 1
        
        # Check new value
        has_new = log.new_value == 'accepted'
        print_test("New status recorded", has_new, f"New: {log.new_value}")
        tests_passed += has_new
        tests_total += 1
        
        # Check user
        correct_user = log.user == driver
        print_test("User recorded", correct_user, f"User: {log.user.email}")
        tests_passed += correct_user
        tests_total += 1
        
        # Check IP
        has_ip = log.ip_address is not None
        print_test("IP address recorded", has_ip, f"IP: {log.ip_address}")
        tests_passed += has_ip
        tests_total += 1
    
    return tests_passed, tests_total

def main():
    """Run all tests"""
    print_header("PHASE 1 ANTI-FRAUD IMPLEMENTATION TEST SUITE")
    
    total_passed = 0
    total_tests = 0
    
    try:
        # Run tests
        passed, total = test_valid_transitions()
        total_passed += passed
        total_tests += total
        
        passed, total = test_invalid_transitions()
        total_passed += passed
        total_tests += total
        
        passed, total = test_unauthorized_access()
        total_passed += passed
        total_tests += total
        
        passed, total = test_audit_logging()
        total_passed += passed
        total_tests += total
        
    except Exception as e:
        print(f"\n{Colors.RED}{Colors.BOLD}ERROR: {str(e)}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        return 1
    
    # Summary
    print_header("TEST SUMMARY")
    passed_pct = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"{Colors.BOLD}Total Tests:{Colors.ENDC} {total_tests}")
    print(f"{Colors.GREEN}{Colors.BOLD}Passed:{Colors.ENDC} {total_passed}")
    print(f"{Colors.RED}{Colors.BOLD}Failed:{Colors.ENDC} {total_tests - total_passed}")
    print(f"{Colors.CYAN}{Colors.BOLD}Success Rate:{Colors.ENDC} {passed_pct:.1f}%")
    
    if total_passed == total_tests:
        print(f"\n{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED - Phase 1 is working correctly!{Colors.ENDC}\n")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED - Please review the output above{Colors.ENDC}\n")
        return 1

if __name__ == '__main__':
    sys.exit(main())
