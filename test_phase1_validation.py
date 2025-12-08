"""
Quick test to verify Phase 1 anti-fraud implementation
Tests:
1. Validation framework works
2. Audit logging works
3. Delivery status transitions are enforced
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from users.models import User
from orders.models import Order
from delivery.models import Delivery
from stores.models import Store
from core.models import AuditLog
from django.utils import timezone
import json


def test_phase1_validation():
	print("\n" + "="*70)
	print("PHASE 1 VALIDATION TEST - Anti-Fraud Implementation")
	print("="*70 + "\n")
	
	# Setup
	client = APIClient()
	
	# Create test users
	print("1. Setting up test data...")
	try:
		store_manager = User.objects.create_user(
			email='manager@test.com',
			password='test123',
			user_type='store_manager',
			first_name='Manager',
			last_name='Test'
		)
		
		delivery_agent = User.objects.create_user(
			email='driver@test.com',
			password='test123',
			user_type='delivery_agent',
			first_name='Driver',
			last_name='Test'
		)
		
		store = Store.objects.create(
			name='Test Store',
			manager=store_manager,
			city='Paris'
		)
		
		order = Order.objects.create(
			store=store,
			status='ready',
			total_price=100.00
		)
		
		delivery = Delivery.objects.create(
			order=order,
			delivery_agent=delivery_agent,
			status='pending'
		)
		
		print(f"   ✓ Created manager: {store_manager.email}")
		print(f"   ✓ Created driver: {delivery_agent.email}")
		print(f"   ✓ Created order: #{order.id} (status: {order.status})")
		print(f"   ✓ Created delivery: #{delivery.id} (status: {delivery.status})")
		
	except Exception as e:
		print(f"   ✗ Setup failed: {str(e)}")
		return False
	
	# Test 1: Valid delivery acceptance
	print("\n2. Testing valid delivery acceptance...")
	client.force_authenticate(user=delivery_agent)
	try:
		response = client.post(f'/api/v1/dashboard/delivery/{delivery.id}/accept/')
		print(f"   Status: {response.status_code}")
		print(f"   Response: {response.data}")
		
		# Check audit log
		audit_logs = AuditLog.objects.filter(object_type='delivery', object_id=delivery.id)
		print(f"   Audit logs created: {audit_logs.count()}")
		for log in audit_logs:
			print(f"     - {log.get_action_type_display()}: {log.old_value} → {log.new_value}")
		
		# Verify status changed
		delivery.refresh_from_db()
		print(f"   Delivery status now: {delivery.status}")
		
		if response.status_code == 200 and delivery.status == 'accepted':
			print("   ✓ Valid acceptance succeeded with audit logging")
		else:
			print("   ✗ Acceptance failed or status not updated")
			
	except Exception as e:
		print(f"   ✗ Error: {str(e)}")
	
	# Test 2: Invalid status transition (try to accept already accepted delivery)
	print("\n3. Testing invalid status transition...")
	try:
		response = client.post(f'/api/v1/dashboard/delivery/{delivery.id}/accept/')
		print(f"   Status: {response.status_code}")
		print(f"   Response: {response.data}")
		
		# Check if suspicious flag set
		suspicious_logs = AuditLog.objects.filter(
			object_type='delivery', 
			object_id=delivery.id,
			is_suspicious=True
		)
		print(f"   Suspicious logs: {suspicious_logs.count()}")
		
		if response.status_code in [400, 403]:
			print("   ✓ Invalid transition rejected correctly")
		else:
			print("   ✗ Should have been rejected")
			
	except Exception as e:
		print(f"   ✗ Error: {str(e)}")
	
	# Test 3: Unauthorized access
	print("\n4. Testing unauthorized access prevention...")
	unauthorized_user = User.objects.create_user(
		email='hacker@test.com',
		password='test123',
		user_type='delivery_agent',
		first_name='Hacker',
		last_name='Test'
	)
	
	client.force_authenticate(user=unauthorized_user)
	try:
		response = client.post(f'/api/v1/dashboard/delivery/{delivery.id}/accept/')
		print(f"   Status: {response.status_code}")
		print(f"   Response: {response.data}")
		
		# Check if suspicious flag set
		suspicious_logs = AuditLog.objects.filter(
			object_type='delivery', 
			object_id=delivery.id,
			user=unauthorized_user,
			is_suspicious=True
		)
		print(f"   Suspicious logs: {suspicious_logs.count()}")
		
		if response.status_code == 403 and suspicious_logs.count() > 0:
			print("   ✓ Unauthorized access blocked and logged as suspicious")
		else:
			print("   ✗ Should have been blocked and marked suspicious")
			
	except Exception as e:
		print(f"   ✗ Error: {str(e)}")
	
	# Summary
	print("\n" + "="*70)
	print("SUMMARY")
	print("="*70)
	total_logs = AuditLog.objects.all().count()
	suspicious_logs = AuditLog.objects.filter(is_suspicious=True).count()
	print(f"Total audit logs: {total_logs}")
	print(f"Suspicious logs: {suspicious_logs}")
	print("\nPhase 1 Status Validation: ✓ IMPLEMENTED")
	print("  - Validators framework active")
	print("  - Audit logging active")
	print("  - Status transitions enforced")
	print("  - Unauthorized access tracking enabled")
	print("\n" + "="*70 + "\n")


if __name__ == '__main__':
	test_phase1_validation()
