#!/usr/bin/env python
"""
Verification Test Script for Operator Fee System
This script demonstrates that the operator fee system is fully functional.
Run with: python verify_operator_fee_system.py
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gaboshop.settings')
django.setup()

from decimal import Decimal
from orders.models import Order
from orders.serializers import OrderSerializer
import json


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(title.center(80))
    print("=" * 80)


def test_operator_fee_system():
    """Comprehensive test of operator fee system"""
    
    print_section("OPERATOR FEE SYSTEM VERIFICATION")
    
    # Get a test order
    order = Order.objects.filter(operator_fee__isnull=False).first()
    
    if not order:
        print("ERROR: No orders found in database")
        return False
    
    success = True
    
    # Test 1: Field exists
    print("\n[TEST 1] Verify operator_fee field exists")
    print("-" * 80)
    try:
        fee_value = order.operator_fee
        print(f"✓ operator_fee field accessible: {fee_value} FCFA")
    except AttributeError as e:
        print(f"✗ ERROR: operator_fee field not found: {e}")
        success = False
    
    # Test 2: Calculate method exists
    print("\n[TEST 2] Verify calculate_operator_fee() method exists")
    print("-" * 80)
    try:
        method = getattr(order, 'calculate_operator_fee', None)
        if callable(method):
            print("✓ calculate_operator_fee() method exists and is callable")
        else:
            print("✗ ERROR: calculate_operator_fee() is not callable")
            success = False
    except AttributeError as e:
        print(f"✗ ERROR: Method not found: {e}")
        success = False
    
    # Test 3: Test all operator rates
    print("\n[TEST 3] Verify operator fee calculations")
    print("-" * 80)
    
    operators = {
        'airtel': ('Airtel Money', Decimal('3.00')),
        'moov': ('Moov Money', Decimal('3.00')),
        'card': ('Card Payment', Decimal('2.50')),
        'cash': ('Cash', Decimal('0.00')),
    }
    
    base_amount = order.items_total + order.delivery_fee
    print(f"Base Amount (items + delivery): {base_amount} FCFA\n")
    
    for operator_key, (operator_name, expected_rate) in operators.items():
        calculated_fee = order.calculate_operator_fee(operator=operator_key)
        expected_fee = (base_amount * expected_rate) / Decimal('100')
        expected_fee = expected_fee.quantize(Decimal('0.01'))
        
        matches = calculated_fee == expected_fee
        status = "✓" if matches else "✗"
        
        print(f"{status} {operator_name:.<30} {calculated_fee:>12} FCFA (Expected: {expected_fee})")
        
        if not matches:
            success = False
    
    # Test 4: Serializer integration
    print("\n[TEST 4] Verify serializer includes operator_fee")
    print("-" * 80)
    
    try:
        serializer = OrderSerializer(order)
        data = serializer.data
        
        # Check main field
        if 'operator_fee' in data:
            print(f"✓ operator_fee field in main response: {data['operator_fee']} FCFA")
        else:
            print("✗ ERROR: operator_fee not in main response fields")
            success = False
        
        # Check invoice breakdown
        if 'invoice_breakdown' in data:
            breakdown = data['invoice_breakdown']
            
            # Check summary
            if 'summary' in breakdown and 'operator_fee' in breakdown['summary']:
                print(f"✓ operator_fee in invoice breakdown summary: {breakdown['summary']['operator_fee']} FCFA")
            else:
                print("✗ ERROR: operator_fee not in invoice breakdown summary")
                success = False
            
            # Check payment breakdown lines
            if 'payment_breakdown' in breakdown:
                lines = breakdown['payment_breakdown'].get('lines', [])
                operator_line_found = False
                
                for line in lines:
                    if 'Frais opérateur' in line.get('description', ''):
                        print(f"✓ operator_fee in payment breakdown lines: {line['amount']} FCFA")
                        operator_line_found = True
                        break
                
                if not operator_line_found and order.operator_fee > 0:
                    print("✗ ERROR: operator_fee line not found in payment breakdown (fee > 0)")
                    success = False
                elif not operator_line_found and order.operator_fee == 0:
                    print("✓ operator_fee line correctly omitted (fee = 0)")
        else:
            print("✗ ERROR: invoice_breakdown not in response")
            success = False
            
    except Exception as e:
        print(f"✗ ERROR during serialization: {e}")
        success = False
    
    # Test 5: Totals include operator fee
    print("\n[TEST 5] Verify total_amount includes operator_fee")
    print("-" * 80)
    
    try:
        # Create a fresh copy and calculate totals
        fresh_order = Order.objects.get(pk=order.pk)
        fresh_order.calculate_totals()
        
        # Verify the formula
        expected_total = (
            fresh_order.items_total +
            fresh_order.delivery_fee +
            fresh_order.service_fee +
            fresh_order.operator_fee +
            fresh_order.tax_amount +
            fresh_order.payment_fees
        )
        
        actual_total = fresh_order.total_amount
        matches = actual_total == expected_total
        status = "✓" if matches else "✗"
        
        print(f"{status} Total calculation:")
        print(f"   Items:       {fresh_order.items_total} FCFA")
        print(f"   Delivery:    {fresh_order.delivery_fee} FCFA")
        print(f"   Service:     {fresh_order.service_fee} FCFA")
        print(f"   Operator:    {fresh_order.operator_fee} FCFA")
        print(f"   Tax:         {fresh_order.tax_amount} FCFA")
        print(f"   Payment:     {fresh_order.payment_fees} FCFA")
        print(f"   ---")
        print(f"   Expected:    {expected_total} FCFA")
        print(f"   Actual:      {actual_total} FCFA")
        
        if not matches:
            success = False
            
    except Exception as e:
        print(f"✗ ERROR during total calculation: {e}")
        success = False
    
    # Final result
    print_section("TEST RESULTS")
    
    if success:
        print("\n✓ ALL TESTS PASSED\n")
        print("The operator fee system is fully functional and ready for production!")
        return True
    else:
        print("\n✗ SOME TESTS FAILED\n")
        print("Please review the errors above.")
        return False


def display_sample_api_response():
    """Display a sample API response with operator fees"""
    
    print_section("SAMPLE API RESPONSE")
    
    order = Order.objects.filter(operator_fee__gt=0).first()
    
    if not order:
        print("No orders with operator fees found")
        return
    
    serializer = OrderSerializer(order)
    data = serializer.data
    
    # Show key parts of response
    response_sample = {
        'order_number': data.get('order_number'),
        'financial_summary': {
            'items_total': data.get('items_total'),
            'delivery_fee': data.get('delivery_fee'),
            'service_fee': data.get('service_fee'),
            'operator_fee': data.get('operator_fee'),
            'total_amount': data.get('total_amount'),
        },
        'invoice_breakdown': data.get('invoice_breakdown'),
    }
    
    print("\nJSON Response (Pretty Printed):\n")
    print(json.dumps(response_sample, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    print("\n")
    print("*" * 80)
    print("GABOSHOP OPERATOR FEE SYSTEM - VERIFICATION TEST".center(80))
    print("*" * 80)
    
    # Run tests
    all_passed = test_operator_fee_system()
    
    # Display sample response
    if all_passed:
        display_sample_api_response()
    
    print_section("CONFIGURATION REFERENCE")
    print("""
Current Operator Fees (in orders/models.py):

    OPERATOR_FEES = {
        'airtel': Decimal('3.00'),      # Airtel Money: 3%
        'moov': Decimal('3.00'),        # Moov Money: 3%
        'card': Decimal('2.50'),        # Card: 2.5%
        'cash': Decimal('0.00'),        # Cash: 0%
    }

To modify fees:
1. Open: orders/models.py
2. Find: calculate_operator_fee() method
3. Edit: OPERATOR_FEES dictionary
4. Restart: Django server

See OPERATOR_FEE_SYSTEM.md for detailed documentation.
""")
    
    print("\n")
