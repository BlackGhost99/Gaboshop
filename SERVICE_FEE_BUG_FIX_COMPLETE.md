# Service Fee Bug Fix - Complete Solution

## Problem Statement
**"Les frais de service sont payés par DEUX entités au lieu d'une seule"**

Sur une commande client final (B2C), le problème était que :
- Le client ET le magasin vendeur pouvaient TOUS LES DEUX payer le service_fee
- C'est de l'escroquerie : une seule entité (l'initiateur) doit payer

---

## Root Cause
La méthode `Order.calculate_service_fee()` ne différenciait pas entre :
1. **B2C** : Seul le client (acheteur final) doit payer le `service_fee`
2. **B2B** : Seul le `source_store` (buyer, celui qui a passé la commande) doit payer le `service_fee_to_wholesaler`

Le vendeur (seller) ne paie JAMAIS de frais de service.

---

## Solution Implemented

### 1. Fixed `Order.calculate_service_fee()` Method
**File**: [orders/models.py](orders/models.py#L207-L230)

```python
def calculate_service_fee(self):
    """
    Calcule les frais de service selon le plan d'abonnement et le type de commande
    
    RÈGLE IMPORTANTE:
    - B2C: seul le CLIENT (qui passe la commande) paie le service_fee
    - B2B: seul le BUYER_STORE (source_store) paie le service_fee_to_wholesaler
    - Le vendeur (store) ne paie JAMAIS de frais de service
    """
    if self.is_b2b and self.source_store:
        # Commande B2B: charger au buyer_store (source_store)
        from payments.subscription_check import SubscriptionChecker
        self.service_fee = SubscriptionChecker.get_service_fee_b2b(self.source_store)
    else:
        # Commande B2C: charger au client via le plan du store vendeur
        plan = self.store.get_current_plan()
        
        if plan and hasattr(plan, 'service_fee_client_amount'):
            self.service_fee = Decimal(str(plan.service_fee_client_amount))
        else:
            # Fallback si pas de plan ou ancien modèle
            self.service_fee = self.store.service_fee if self.store.service_fee > 0 else Decimal('500.00')
    
    return self.service_fee
```

### 2. Added Comprehensive Unit Tests
**File**: [payments/tests/test_service_fee_bug.py](payments/tests/test_service_fee_bug.py)

Three test scenarios ensure the fix is correct:

#### Test 1: B2C Order - Client Pays Only
- Order is B2C (`is_b2b=False`, `source_store=None`)
- Client pays: Items + Delivery + Service Fee
- Store pays: Commission only (NOT service fee)
- ✓ Service fee = 500 FCFA (from plan)

#### Test 2: B2B Order - Buyer Pays Only
- Order is B2B (`is_b2b=True`, `source_store=buyer_store`)
- Buyer store pays: Items + Delivery + Service Fee (B2B amount)
- Seller (wholesaler) pays: Commission only (NOT service fee)
- ✓ Service fee = 1000 FCFA (from SubscriptionChecker.get_service_fee_b2b())

#### Test 3: Reversement Calculation
- Service fee (paid by client/buyer) is NOT deducted from store's payout
- Store receives: Items Total - Commission + Delivery Share
- Service Fee belongs to GABOSHOP (platform)
- ✓ Double-deduction bug prevented

---

## Test Results
```
Ran 3 tests in 13.287s - OK (all passed)

[B2C Test] Client pays: Items (15000) + Delivery (2000) + Service (500) = Total (17500)
[B2C Test] Store pays: Commission (1200.00)

[B2B Test] Buyer pays: Items (75000) + Delivery (5000) + Service (1000) = Total (81000.00)
[B2B Test] Seller (Wholesaler) pays: Commission (6000.00)

[Reversement Test] Client paid: 17500.00 (including 500 service fee)
[Reversement Test] Store receives: 14600.000 (items - commission + delivery_share)
[Reversement Test] GABOSHOP keeps: Commission 1200.00 + Service Fee 500 + Delivery Share 800.000 = 2500.000
```

---

## Financial Impact

### Before Fix (WRONG)
**B2C Order Example**: Items 15,000 + Delivery 2,000
- Client was charged: 15,000 + 2,000 + **500** = 17,500 ❌
- Store was also charged: **500** (service fee) ❌❌ **DOUBLE CHARGE!**
- GABOSHOP received: 500 (from client) + 500 (from store) = **1,000 FCFA** ❌ **FRAUD**

### After Fix (CORRECT)
**B2C Order Example**: Items 15,000 + Delivery 2,000
- Client pays: 15,000 + 2,000 + **500** = 17,500 ✓
- Store pays: Commission only (8% of 15,000 = 1,200) ✓
- GABOSHOP receives: 500 (service fee) + 1,200 (commission) + 800 (delivery share) = **2,500 FCFA** ✓

---

## Files Modified
1. **[orders/models.py](orders/models.py#L207-L230)** - Fixed `Order.calculate_service_fee()` method
2. **[payments/tests/test_service_fee_bug.py](payments/tests/test_service_fee_bug.py)** - Added 3 comprehensive unit tests

---

## Verification Checklist
- [x] B2C orders: Client pays service fee, store does not
- [x] B2B orders: Buyer pays service fee, seller does not
- [x] Commission calculation: Not affected by service fee
- [x] Reversement logic: Service fee not double-deducted
- [x] All 3 unit tests passing
- [x] No regressions in existing tests

---

## Deployment Notes
1. No database migration required (column already exists)
2. The fix applies to **new orders created after deployment**
3. **Existing orders** with double charges should be manually reviewed and corrected via admin

---

## Related Code
- `payments/subscription_check.py` - `get_service_fee_b2b()` method (used for B2B charges)
- `orders/models.py` - `Order.calculate_commission()` and `calculate_totals()` methods
- `b2b/services/supply.py` - B2B order creation flow

---

## Date Completed
**January 13, 2026**

## Status
✅ **FIXED AND TESTED**
