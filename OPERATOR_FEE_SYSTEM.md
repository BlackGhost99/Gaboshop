# Operator Fee System Documentation

## Overview

The Gaboshop payment system now includes a **scalable operator fee system** that charges customers for payment processing fees based on their chosen payment method. This is a configurable system that allows easy updates to fee rates without code changes.

## Current Configuration

### Supported Operators and Fee Rates

| Operator | Type | Fee Rate | Description |
|----------|------|----------|-------------|
| `airtel` | Mobile Money | 3% | Airtel Money mobile wallet |
| `moov` | Mobile Money | 3% | Moov Money mobile wallet |
| `card` | Card Payment | 2.5% | Credit/Debit card payments |
| `cash` | Cash | 0% | Cash on delivery (no fee) |

### Fee Calculation

The operator fee is calculated based on:
- **Base Amount** = `items_total` + `delivery_fee`
- **Operator Fee** = `base_amount × fee_rate / 100`

**Example:**
```
Items Total:      15,000 FCFA
Delivery Fee:      2,000 FCFA
Base Amount:      17,000 FCFA

Airtel (3%):      17,000 × 3% = 510 FCFA
```

## Implementation Details

### 1. Database Model (`orders/models.py`)

#### Field Definition
```python
operator_fee = models.DecimalField(
    max_digits=8,
    decimal_places=2,
    default=0.00,
    help_text="Frais opérateur Mobile Money (Airtel/Moov)"
)
```

#### Method: `calculate_operator_fee()`
```python
def calculate_operator_fee(self, operator='airtel', payment_method='mobile_money'):
    """
    Calculate operator fee based on payment method and operator.
    
    Args:
        operator (str): 'airtel', 'moov', 'card', or 'cash'
        payment_method (str): 'mobile_money', 'card', 'cash'
    
    Returns:
        Decimal: Calculated operator fee
    """
```

#### Configuration Dictionary
Located in the `calculate_operator_fee()` method:
```python
OPERATOR_FEES = {
    'airtel': Decimal('3.00'),
    'moov': Decimal('3.00'),
    'card': Decimal('2.50'),
    'cash': Decimal('0.00'),
}
```

### 2. Serializer Integration (`orders/serializers.py`)

The `OrderSerializer` exposes the operator fee in multiple places:

#### Fields Exposed
- `operator_fee` in main field list
- `operator_fee` in read-only fields

#### Invoice Breakdown Integration
The `get_invoice_breakdown()` method automatically includes:

```json
{
  "invoice_breakdown": {
    "summary": {
      "items_total": "15000.00",
      "delivery_fee": "2000.00",
      "service_fee": "500.00",
      "operator_fee": "510.00",      // NEW FIELD
      "tax_amount": "0.00",
      "payment_fees": "0.00",
      "total_amount": "18010.00"
    },
    "payment_breakdown": {
      "lines": [
        {
          "description": "Sous-total (articles)",
          "amount": "15000.00"
        },
        {
          "description": "Frais de livraison",
          "amount": "2000.00"
        },
        {
          "description": "Frais de service plateforme",
          "amount": "500.00"
        },
        {
          "description": "Frais opérateur Mobile Money (Airtel/Moov)",
          "amount": "510.00"        // NEW LINE ITEM
        },
        {
          "description": "TOTAL A PAYER",
          "amount": "18010.00"
        }
      ]
    }
  }
}
```

### 3. Automatic Calculation

The operator fee is automatically calculated and included in the total when `calculate_totals()` is called:

```python
def calculate_totals(self):
    """Calculate all order totals including operator fee"""
    # ... other calculations ...
    self.operator_fee = self.calculate_operator_fee()  # Called here
    self.total_amount = (
        self.items_total +
        self.delivery_fee +
        self.service_fee +
        self.operator_fee +      # Included in total
        self.tax_amount +
        self.payment_fees
    )
```

## API Response Example

### GET `/api/orders/{id}/`

```json
{
  "id": 123,
  "order_number": "CMD58214884",
  "client": "John Doe",
  "status": "pending",
  "status_display": "En attente",
  "items_total": "15000.00",
  "delivery_fee": "2000.00",
  "service_fee": "500.00",
  "operator_fee": "510.00",
  "tax_amount": "0.00",
  "payment_fees": "0.00",
  "total_amount": "18010.00",
  "invoice_breakdown": {
    "items": [
      {
        "product_name": "Product A",
        "quantity": 1,
        "unit_price": "15000.00",
        "subtotal": "15000.00"
      }
    ],
    "summary": {
      "items_total": "15000.00",
      "delivery_fee": "2000.00",
      "service_fee": "500.00",
      "operator_fee": "510.00",
      "tax_amount": "0.00",
      "payment_fees": "0.00",
      "total_amount": "18010.00"
    },
    "payment_breakdown": {
      "currency": "FCFA",
      "lines": [
        {"description": "Sous-total (articles)", "amount": "15000.00"},
        {"description": "Frais de livraison", "amount": "2000.00"},
        {"description": "Frais de service plateforme", "amount": "500.00"},
        {"description": "Frais opérateur Mobile Money (Airtel/Moov)", "amount": "510.00"},
        {"description": "TOTAL A PAYER", "amount": "18010.00"}
      ]
    }
  }
}
```

## Modification Guide

### To Change Operator Fee Rates

Edit `orders/models.py` in the `calculate_operator_fee()` method:

```python
OPERATOR_FEES = {
    'airtel': Decimal('3.50'),    # Changed from 3% to 3.5%
    'moov': Decimal('3.00'),
    'card': Decimal('2.50'),
    'cash': Decimal('0.00'),
}
```

Then restart the Django server.

### To Add a New Payment Operator

1. Add to the `OPERATOR_FEES` dictionary:
```python
OPERATOR_FEES = {
    'airtel': Decimal('3.00'),
    'moov': Decimal('3.00'),
    'card': Decimal('2.50'),
    'cash': Decimal('0.00'),
    'wave': Decimal('2.00'),      # NEW OPERATOR
}
```

2. Call with the new operator:
```python
order.calculate_operator_fee(operator='wave')
```

### Future Enhancement: Django Settings

To make the configuration even more scalable, move the dictionary to Django settings:

```python
# settings.py
OPERATOR_FEES = {
    'airtel': '3.00',
    'moov': '3.00',
    'card': '2.50',
    'cash': '0.00',
}

# orders/models.py
from django.conf import settings
from decimal import Decimal

def calculate_operator_fee(self, operator='airtel', payment_method='mobile_money'):
    base_amount = self.items_total + self.delivery_fee
    
    fee_rate_str = settings.OPERATOR_FEES.get(operator.lower(), '0.00')
    fee_rate = Decimal(fee_rate_str)
    
    operator_fee = (base_amount * fee_rate) / Decimal('100')
    return operator_fee.quantize(Decimal('0.01'))
```

### Future Enhancement: Admin Panel Configuration

Create a Django model for dynamic fee configuration:

```python
class OperatorFeeConfig(models.Model):
    operator = models.CharField(max_length=20, unique=True)
    fee_rate = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=100)
    active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.operator} - {self.fee_rate}%"
```

Then modify the calculation to use this model:

```python
def calculate_operator_fee(self, operator='airtel', payment_method='mobile_money'):
    base_amount = self.items_total + self.delivery_fee
    
    try:
        config = OperatorFeeConfig.objects.get(
            operator=operator.lower(),
            active=True
        )
        fee_rate = config.fee_rate
    except OperatorFeeConfig.DoesNotExist:
        fee_rate = Decimal('0.00')
    
    operator_fee = (base_amount * fee_rate) / Decimal('100')
    return operator_fee.quantize(Decimal('0.01'))
```

## Testing

### Unit Test Examples

```python
def test_operator_fee_calculation():
    order = Order.objects.create(
        items_total=Decimal('10000.00'),
        delivery_fee=Decimal('2000.00'),
    )
    
    # Test Airtel (3%)
    airtel_fee = order.calculate_operator_fee(operator='airtel')
    assert airtel_fee == Decimal('360.00')  # 12000 * 3%
    
    # Test Moov (3%)
    moov_fee = order.calculate_operator_fee(operator='moov')
    assert moov_fee == Decimal('360.00')
    
    # Test Card (2.5%)
    card_fee = order.calculate_operator_fee(operator='card')
    assert card_fee == Decimal('300.00')
    
    # Test Cash (0%)
    cash_fee = order.calculate_operator_fee(operator='cash')
    assert cash_fee == Decimal('0.00')

def test_total_includes_operator_fee():
    order = Order.objects.create(
        items_total=Decimal('15000.00'),
        delivery_fee=Decimal('2000.00'),
        service_fee=Decimal('500.00'),
    )
    
    order.calculate_totals()
    
    # Total should include operator fee
    expected_operator_fee = Decimal('510.00')  # 17000 * 3%
    expected_total = Decimal('18010.00')
    
    assert order.operator_fee == expected_operator_fee
    assert order.total_amount == expected_total
```

## Database Migration

The migration for the `operator_fee` field has already been created:

```bash
# File: orders/migrations/0005_order_operator_fee.py
```

To apply the migration if needed:

```bash
python manage.py migrate orders
```

## Key Features

✅ **Decimal Precision**: Uses Python's `Decimal` type for accurate financial calculations
✅ **Automatic Calculation**: Operator fee is calculated automatically in `calculate_totals()`
✅ **Client Transparency**: Fee is clearly displayed in invoice breakdown
✅ **Scalable Configuration**: Easy to modify rates without code changes
✅ **Multiple Operators**: Supports different payment methods with different fee rates
✅ **Zero-Fee Option**: Supports operators with 0% fees (like cash)
✅ **API Integrated**: Fully exposed in REST API responses

## Summary

The operator fee system provides a flexible, scalable way to charge customers for payment processing costs. It's fully integrated with the invoice system and transparently displayed to clients. Fee rates can be easily modified and the system supports unlimited operators.
