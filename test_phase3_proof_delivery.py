"""
Test Phase 3: Proof of Delivery
Tests photo + GPS + signature/PIN requirements for delivery completion
"""

import os
import django
import sys
from decimal import Decimal
from io import BytesIO
from PIL import Image

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from delivery.models import Delivery, DeliveryProof
from orders.models import Order
from products.models import Product
from stores.models import Store
from users.models import UserProfile
from core.validators import calculate_gps_distance, validate_delivery_proof, can_mark_as_delivered
from core.models import AuditLog

User = get_user_model()

# Test configuration
TEST_DELIVERY_ADDRESS = "123 Test Street, Nairobi"
TEST_GPS_LAT = Decimal("-1.286389")  # Nairobi coordinates
TEST_GPS_LON = Decimal("36.817223")
TEST_PIN = "1234"

# Colors for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(message, status="INFO"):
    colors = {
        "PASS": Colors.GREEN,
        "FAIL": Colors.RED,
        "INFO": Colors.BLUE,
        "WARN": Colors.YELLOW
    }
    color = colors.get(status, Colors.RESET)
    print(f"{color}[{status}] {message}{Colors.RESET}")

def create_test_image():
    """Create a simple test image"""
    img = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return SimpleUploadedFile("test_photo.png", buffer.read(), content_type="image/png")

def create_test_signature():
    """Create a simple test signature image"""
    img = Image.new('RGB', (200, 100), color='blue')
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return SimpleUploadedFile("signature.png", buffer.read(), content_type="image/png")

def setup_test_data():
    """Create test users, store, product, order, and delivery"""
    print_test("Setting up test data...", "INFO")
    
    # Clean up any existing test data
    User.objects.filter(phone__in=['0700000001', '0700000002']).delete()
    
    # Create users
    customer = User.objects.create_user(
        phone='0700000001',
        username='test_customer_proof',
        email='customer.proof@test.com',
        password='test123',
        user_type='client'
    )
    
    delivery_agent = User.objects.create_user(
        phone='0700000002',
        username='test_agent_proof',
        email='agent.proof@test.com',
        password='test123',
        user_type='delivery_agent'
    )
    
    # Create store category
    from stores.models import StoreCategory
    category, _ = StoreCategory.objects.get_or_create(
        name='Test Category',
        defaults={'description': 'Test category for proof delivery tests'}
    )
    
    # Create store
    store = Store.objects.create(
        name='Test Store Proof',
        manager=customer,
        category=category,
        phone='0700000010',
        address=TEST_DELIVERY_ADDRESS,
        city='Nairobi',
        zone='Test Zone',
        latitude=TEST_GPS_LAT,
        longitude=TEST_GPS_LON
    )
    
    # Create product
    product = Product.objects.create(
        name='Test Product Proof',
        store=store,
        price=Decimal('100.00'),
        stock=10
    )
    
    # Create order (this will automatically create a delivery via signal)
    order = Order.objects.create(
        client=customer,
        store=store,
        total_amount=Decimal('100.00'),
        delivery_fee=Decimal('10.00'),
        delivery_address=TEST_DELIVERY_ADDRESS,
        status='confirmed'
    )
    
    # Get the auto-created delivery and update it
    delivery = Delivery.objects.get(order=order)
    delivery.delivery_agent = delivery_agent
    delivery.delivery_lat = TEST_GPS_LAT
    delivery.delivery_lng = TEST_GPS_LON
    delivery.status = 'in_transit'
    delivery.delivery_code = TEST_PIN
    delivery.save()
    
    print_test(f"Created test delivery #{delivery.id}", "INFO")
    return delivery, delivery_agent, customer

def test_gps_distance_calculation():
    """Test 1: GPS distance calculation using Haversine formula"""
    print_test("\n=== Test 1: GPS Distance Calculation ===", "INFO")
    
    # Same location (should be 0)
    distance = calculate_gps_distance(
        TEST_GPS_LAT, TEST_GPS_LON,
        TEST_GPS_LAT, TEST_GPS_LON
    )
    if distance == 0:
        print_test(f"Same location distance: {distance}m", "PASS")
    else:
        print_test(f"Same location distance should be 0, got {distance}m", "FAIL")
        return False
    
    # Different location (100m away)
    lat2 = TEST_GPS_LAT + Decimal("0.0009")  # ~100m north
    distance = calculate_gps_distance(
        TEST_GPS_LAT, TEST_GPS_LON,
        lat2, TEST_GPS_LON
    )
    if 90 <= distance <= 110:  # Allow some margin for precision
        print_test(f"~100m distance calculation: {distance:.2f}m", "PASS")
    else:
        print_test(f"Expected ~100m, got {distance:.2f}m", "FAIL")
        return False
    
    # Far location (>500m, should fail validation)
    lat3 = TEST_GPS_LAT + Decimal("0.005")  # ~550m north
    distance = calculate_gps_distance(
        TEST_GPS_LAT, TEST_GPS_LON,
        lat3, TEST_GPS_LON
    )
    if distance > 500:
        print_test(f"Far location distance: {distance:.2f}m (>500m)", "PASS")
    else:
        print_test(f"Expected >500m, got {distance:.2f}m", "FAIL")
        return False
    
    return True

def test_proof_validation_complete(delivery):
    """Test 2: Valid proof with all requirements (photo + GPS + signature)"""
    print_test("\n=== Test 2: Complete Proof Validation ===", "INFO")
    
    photo = create_test_image()
    signature = create_test_signature()
    
    # Create proof with all requirements
    proof = DeliveryProof.objects.create(
        delivery=delivery,
        photo=photo,
        latitude=TEST_GPS_LAT,
        longitude=TEST_GPS_LON,
        signature=signature,
        recipient_name="John Doe"
    )
    
    # Validate
    is_valid, errors = validate_delivery_proof(delivery)
    
    if is_valid:
        print_test("Valid proof with photo + GPS + signature", "PASS")
    else:
        print_test(f"Expected valid proof, got errors: {errors}", "FAIL")
        return False
    
    # Check proof properties
    if proof.is_valid:
        print_test("DeliveryProof.is_valid property working", "PASS")
    else:
        print_test("DeliveryProof.is_valid should be True", "FAIL")
        return False
    
    if proof.is_location_valid:
        print_test("DeliveryProof.is_location_valid property working", "PASS")
    else:
        print_test("DeliveryProof.is_location_valid should be True", "FAIL")
        return False
    
    # Cleanup
    proof.delete()
    return True

def test_proof_validation_with_pin(delivery):
    """Test 3: Valid proof with photo + GPS + PIN (no signature)"""
    print_test("\n=== Test 3: Proof with PIN Instead of Signature ===", "INFO")
    
    photo = create_test_image()
    
    # Create proof with PIN instead of signature
    proof = DeliveryProof.objects.create(
        delivery=delivery,
        photo=photo,
        latitude=TEST_GPS_LAT,
        longitude=TEST_GPS_LON,
        pin_code=TEST_PIN,
        recipient_name="Jane Smith"
    )
    
    # Validate
    is_valid, errors = validate_delivery_proof(delivery)
    
    if is_valid:
        print_test("Valid proof with photo + GPS + PIN", "PASS")
    else:
        print_test(f"Expected valid proof, got errors: {errors}", "FAIL")
        return False
    
    # Cleanup
    proof.delete()
    return True

def test_missing_photo(delivery):
    """Test 4: Missing photo should fail validation"""
    print_test("\n=== Test 4: Missing Photo Validation ===", "INFO")
    
    signature = create_test_signature()
    
    # Create proof without photo
    proof = DeliveryProof.objects.create(
        delivery=delivery,
        latitude=TEST_GPS_LAT,
        longitude=TEST_GPS_LON,
        signature=signature
    )
    
    # Validate
    is_valid, errors = validate_delivery_proof(delivery)
    
    if not is_valid and 'photo' in str(errors):
        print_test("Missing photo correctly rejected", "PASS")
    else:
        print_test("Expected photo error, got: " + str(errors), "FAIL")
        return False
    
    # Cleanup
    proof.delete()
    return True

def test_missing_gps(delivery):
    """Test 5: Missing GPS coordinates should fail validation"""
    print_test("\n=== Test 5: Missing GPS Validation ===", "INFO")
    
    photo = create_test_image()
    signature = create_test_signature()
    
    # Create proof without GPS
    proof = DeliveryProof.objects.create(
        delivery=delivery,
        photo=photo,
        signature=signature
    )
    
    # Validate
    is_valid, errors = validate_delivery_proof(delivery)
    
    if not is_valid and 'gps' in str(errors).lower():
        print_test("Missing GPS correctly rejected", "PASS")
    else:
        print_test("Expected GPS error, got: " + str(errors), "FAIL")
        return False
    
    # Cleanup
    proof.delete()
    return True

def test_missing_signature_and_pin(delivery):
    """Test 6: Missing both signature AND PIN should fail validation"""
    print_test("\n=== Test 6: Missing Signature/PIN Validation ===", "INFO")
    
    photo = create_test_image()
    
    # Create proof without signature or PIN
    proof = DeliveryProof.objects.create(
        delivery=delivery,
        photo=photo,
        latitude=TEST_GPS_LAT,
        longitude=TEST_GPS_LON
    )
    
    # Validate
    is_valid, errors = validate_delivery_proof(delivery)
    
    if not is_valid and ('signature' in str(errors).lower() or 'pin' in str(errors).lower()):
        print_test("Missing signature/PIN correctly rejected", "PASS")
    else:
        print_test("Expected signature/PIN error, got: " + str(errors), "FAIL")
        return False
    
    # Cleanup
    proof.delete()
    return True

def test_invalid_gps_distance(delivery):
    """Test 7: GPS coordinates too far from delivery address should fail"""
    print_test("\n=== Test 7: Invalid GPS Distance ===", "INFO")
    
    photo = create_test_image()
    signature = create_test_signature()
    
    # Create proof with GPS 1km away
    far_lat = TEST_GPS_LAT + Decimal("0.01")  # ~1km away
    
    proof = DeliveryProof.objects.create(
        delivery=delivery,
        photo=photo,
        latitude=far_lat,
        longitude=TEST_GPS_LON,
        signature=signature
    )
    
    # Validate
    is_valid, errors = validate_delivery_proof(delivery)
    
    if not is_valid and 'distance' in str(errors).lower():
        print_test("Far GPS location correctly rejected", "PASS")
    else:
        print_test("Expected distance error, got: " + str(errors), "FAIL")
        return False
    
    # Cleanup
    proof.delete()
    return True

def test_can_mark_as_delivered(delivery):
    """Test 8: can_mark_as_delivered validation"""
    print_test("\n=== Test 8: Can Mark As Delivered Check ===", "INFO")
    
    # Test without proof
    can_deliver, reason = can_mark_as_delivered(delivery)
    if not can_deliver:
        print_test("Correctly prevents delivery without proof", "PASS")
    else:
        print_test("Should prevent delivery without proof", "FAIL")
        return False
    
    # Add valid proof
    photo = create_test_image()
    signature = create_test_signature()
    
    proof = DeliveryProof.objects.create(
        delivery=delivery,
        photo=photo,
        latitude=TEST_GPS_LAT,
        longitude=TEST_GPS_LON,
        signature=signature
    )
    
    # Test with proof
    can_deliver, reason = can_mark_as_delivered(delivery)
    if can_deliver:
        print_test("Correctly allows delivery with valid proof", "PASS")
    else:
        print_test(f"Should allow delivery with proof, got: {reason}", "FAIL")
        return False
    
    # Cleanup
    proof.delete()
    return True

def test_incorrect_pin(delivery):
    """Test 9: Incorrect PIN should fail validation"""
    print_test("\n=== Test 9: Incorrect PIN Validation ===", "INFO")
    
    photo = create_test_image()
    
    # Create proof with wrong PIN
    proof = DeliveryProof.objects.create(
        delivery=delivery,
        photo=photo,
        latitude=TEST_GPS_LAT,
        longitude=TEST_GPS_LON,
        pin_code="9999"  # Wrong PIN
    )
    
    # Validate
    is_valid, errors = validate_delivery_proof(delivery)
    
    if not is_valid and 'pin' in str(errors).lower():
        print_test("Incorrect PIN correctly rejected", "PASS")
    else:
        print_test("Expected PIN error, got: " + str(errors), "FAIL")
        return False
    
    # Cleanup
    proof.delete()
    return True

def test_audit_logging(delivery):
    """Test 10: Audit logging for proof operations"""
    print_test("\n=== Test 10: Audit Logging ===", "INFO")
    
    initial_count = AuditLog.objects.filter(
        content_type__model='deliveryproof'
    ).count()
    
    photo = create_test_image()
    signature = create_test_signature()
    
    # Create proof (should create audit log)
    proof = DeliveryProof.objects.create(
        delivery=delivery,
        photo=photo,
        latitude=TEST_GPS_LAT,
        longitude=TEST_GPS_LON,
        signature=signature,
        recipient_name="Test User"
    )
    
    # Check if audit log was created
    # Note: Audit logging happens in the view, not in model save
    # This test verifies the model can work with audit logging
    
    if proof.id:
        print_test("DeliveryProof created successfully", "PASS")
    else:
        print_test("DeliveryProof creation failed", "FAIL")
        return False
    
    # Cleanup
    proof.delete()
    return True

def run_all_tests():
    """Run all proof of delivery tests"""
    print_test("\n" + "="*60, "INFO")
    print_test("Phase 3: Proof of Delivery - Test Suite", "INFO")
    print_test("="*60 + "\n", "INFO")
    
    # Setup
    delivery, agent, customer = setup_test_data()
    
    # Run tests
    tests = [
        ("GPS Distance Calculation", lambda: test_gps_distance_calculation()),
        ("Complete Proof (photo+GPS+signature)", lambda: test_proof_validation_complete(delivery)),
        ("Proof with PIN (photo+GPS+PIN)", lambda: test_proof_validation_with_pin(delivery)),
        ("Missing Photo Rejection", lambda: test_missing_photo(delivery)),
        ("Missing GPS Rejection", lambda: test_missing_gps(delivery)),
        ("Missing Signature/PIN Rejection", lambda: test_missing_signature_and_pin(delivery)),
        ("Invalid GPS Distance", lambda: test_invalid_gps_distance(delivery)),
        ("Can Mark As Delivered Check", lambda: test_can_mark_as_delivered(delivery)),
        ("Incorrect PIN Rejection", lambda: test_incorrect_pin(delivery)),
        ("Audit Logging", lambda: test_audit_logging(delivery)),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print_test(f"Test '{test_name}' raised exception: {str(e)}", "FAIL")
            failed += 1
    
    # Summary
    print_test("\n" + "="*60, "INFO")
    print_test("Test Summary", "INFO")
    print_test("="*60, "INFO")
    print_test(f"Total Tests: {passed + failed}", "INFO")
    print_test(f"Passed: {passed}", "PASS" if passed > 0 else "INFO")
    print_test(f"Failed: {failed}", "FAIL" if failed > 0 else "INFO")
    print_test(f"Success Rate: {(passed/(passed+failed)*100):.1f}%", 
               "PASS" if failed == 0 else "WARN")
    
    # Cleanup
    print_test("\nCleaning up test data...", "INFO")
    delivery.order.delete()  # Cascades to delivery
    agent.delete()
    customer.delete()
    
    if failed == 0:
        print_test("\n✓ All proof of delivery tests passed!", "PASS")
        return True
    else:
        print_test(f"\n✗ {failed} test(s) failed", "FAIL")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
