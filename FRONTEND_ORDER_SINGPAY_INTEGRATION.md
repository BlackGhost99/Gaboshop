# Frontend Order Creation & SingPay Integration Flow

## 📋 Quick Summary

**Frontend File:** [frontend/src/pages/client/ClientDashboard.jsx](frontend/src/pages/client/ClientDashboard.jsx)  
**Order Service:** [frontend/src/services/orderService.js](frontend/src/services/orderService.js)  
**Payment Service:** [frontend/src/services/paymentService.js](frontend/src/services/paymentService.js)  
**Backend Order Endpoint:** `POST /api/v1/orders/create/` (see [api/v1/orders.py](api/v1/orders.py))  
**Backend Payment Init:** `POST /orders/{orderId}/payments/init/` (see [api/v1/payments.py](api/v1/payments.py))  
**SingPay Utils:** [payments/utils.py](payments/utils.py) & [payments/services.py](payments/services.py)

---

## 🎯 Frontend: Order Creation Request Body

### Step 1: Building the Payload in ClientDashboard.jsx

**Location:** [frontend/src/pages/client/ClientDashboard.jsx](frontend/src/pages/client/ClientDashboard.jsx#L307-L317)

When user clicks "Passer la commande", the `handleSubmitOrder()` function builds:

```javascript
const payload = {
  store: storeId,                              // Store ID (e.g., 1)
  city,                                        // City (default: 'Libreville')
  delivery_address,                            // User's delivery address
  delivery_phone,                              // User's phone number
  delivery_zone,                               // Zone/quartier name (e.g., "Gayet")
  delivery_requested: form.delivery_requested !== false,  // Boolean (true/false)
  notes: form.notes || '',                     // Optional order notes
  items: items.map((it) => ({                  // Array of items
    product_id: it.id,
    quantity: it.quantity || 1
  }))
};
```

**Important:** The `payment_method` is **NOT** sent in the initial order creation request.  
It's stored in form state but used **after** order creation for payment initialization.

### Step 2: POST to `/api/v1/orders/create/`

**Location:** [frontend/src/services/orderService.js](frontend/src/services/orderService.js#L3-L10)

```javascript
export const createOrder = async (payload) => {
  try {
    const res = await api.post('/orders/create/', payload);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};
```

---

## 💳 Frontend: Payment Initialization (After Order Created)

### Step 3: Payment Method Selection

**Location:** [frontend/src/pages/client/ClientDashboard.jsx](frontend/src/pages/client/ClientDashboard.jsx#L668-L669)

Form dropdown for payment method:
```html
<select
  className="w-full border border-gray-200 rounded-md px-3 py-2"
  value={storeForms[storeName]?.payment_method || 'airtel_money'}
  onChange={(e) => handleChangeForm(storeName, 'payment_method', e.target.value)}
>
  <option value="airtel_money">Airtel Money</option>
  <option value="moov_money">Moov Money</option>
</select>
```

**Current Frontend Payment Methods:**
- `airtel_money` → Airtel Money Mobile Payment
- `moov_money` → Moov Money Mobile Payment

**Note:** SingPay is integrated on the **backend only** (not exposed in frontend UI currently).

### Step 4: Init Payment Request

**Location:** [frontend/src/pages/client/ClientDashboard.jsx](frontend/src/pages/client/ClientDashboard.jsx#L327-L333)

After successful order creation:
```javascript
const payRes = await initPayment(orderId, {
  payment_method,              // 'airtel_money' or 'moov_money'
  phone_number: delivery_phone, // Client's phone for payment prompt
});
```

### Step 5: Calling initPayment Service

**Location:** [frontend/src/services/paymentService.js](frontend/src/services/paymentService.js#L3-L9)

```javascript
export const initPayment = async (orderId, payload) => {
  try {
    const res = await api.post(`/orders/${orderId}/payments/init/`, payload);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};
```

---

## 🔧 Backend: Order Creation (OrderCreateView)

**File:** [api/v1/orders.py](api/v1/orders.py)

```python
class OrderCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = OrderCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            order = serializer.save()
            return Response({
                'success': True,
                'message': 'Commande créée avec succès.',
                'data': OrderSerializer(order).data
            }, status=status.HTTP_201_CREATED)
        
        return Response({
            'success': False,
            'error': {
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'Impossible de créer la commande.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)
```

**What happens:**
1. Validates order data (store, delivery info, items)
2. Creates Order record in database
3. Calculates delivery costs
4. Returns order ID to frontend

---

## 💰 Backend: Payment Initialization with SingPay

**File:** [api/v1/payments.py](api/v1/payments.py#L23-L160)

### PaymentInitView Endpoint

```
POST /orders/{orderId}/payments/init/
```

**Request Payload:**
```json
{
  "payment_method": "airtel_money" or "moov_money",
  "phone_number": "+241XXXXXXXXX",
  "operator": "airtel" (optional)
}
```

### Backend Flow:

1. **Validates payment method** - only `airtel_money` or `moov_money` allowed
   
2. **Calculates fees** - Mobile Money charges 3% fee (added to order total)
   ```python
   if payment_method in ['airtel_money', 'moov_money']:
       fees_rate = Decimal('0.03')  # 3%
       fees = (order.total_amount * fees_rate).quantize(Decimal('0.01'))
       order.payment_fees = fees
       order.calculate_totals()
   ```

3. **Creates or updates Payment record**
   ```python
   payment, created = Payment.objects.get_or_create(
       order=order,
       defaults={
           'payment_method': payment_method,
           'amount': order.total_amount,
           'fees_amount': order.payment_fees,
           'status': 'pending',
           'client_phone': phone_number,
           'transaction_id': f"PAY-{order.order_number}-{timestamp}",
       }
   )
   ```

4. **Calls PaymentService to init SingPay**
   ```python
   formatted_phone = PaymentService._format_gabon_phone(phone_number, operator)
   api_result = PaymentService._call_operator_api(
       operator, formatted_phone, order.total_amount, order
   )
   ```

5. **Returns payment info to frontend**
   ```json
   {
     "success": true,
     "data": {
       "payment": {...},
       "next_steps": {
         "message": "Un prompt de paiement apparaitra sur votre mobile Airtel",
         "action": "Verifiez votre telephone et entrez votre PIN"
       }
     }
   }
   ```

---

## 🎪 PaymentService: SingPay Integration

**File:** [payments/services.py](payments/services.py)

### Operator API Routing

```python
@staticmethod
def _call_operator_api(operator, phone, amount, order):
    if operator == 'airtel':
        return PaymentService._call_airtel_money_api(phone, amount, order)
    elif operator == 'moov':
        return PaymentService._call_moov_money_api(phone, amount, order)
```

### Airtel Money SingPay Integration

**Location:** [payments/services.py](payments/services.py#L104-L147)

```python
@staticmethod
def _call_airtel_money_api(phone, amount, order):
    try:
        response = call_singpay_payment(
            "airtel",
            amount=amount,
            reference=f"GABOSHOP_{order.order_number}",
            phone=phone,
            portefeuille=getattr(settings, "SINGPAY_WALLET_ID", ""),
            disbursement=getattr(settings, "SINGPAY_DISBURSEMENT_ID", ""),
            is_transfer=getattr(settings, 'SINGPAY_ENABLE_TRANSFER', False),
        )

        if response.get("error"):
            raise Exception(response["error"])

        tx = response.get("transaction") or {}
        status_payload = response.get("status") or {}
        
        if status_payload.get("success") is False:
            raise Exception(status_payload.get("message") or "SingPay error")
        
        transaction_id = (
            tx.get("airtel_money_id") or 
            tx.get("id") or 
            f"AIRTEL_{order.id}_{int(timezone.now().timestamp())}"
        )

        return {
            "transaction_id": transaction_id,
            "operator_reference": tx.get("id") or "",
            "status": "pending",
            "next_steps": {
                "message": "Un prompt de paiement apparaitra sur votre mobile Airtel",
                "action": "Verifiez votre telephone et entrez votre PIN",
                "singpay_status": status_payload,
            },
            "raw": response,
        }
    except Exception as e:
        logger.error(f"Erreur Airtel Money API: {e}")
        raise
```

### Similar for Moov Money

**Location:** [payments/services.py](payments/services.py#L153-L195)

---

## 🌐 SingPay API Utilities

**File:** [payments/utils.py](payments/utils.py)

### Calling SingPay Payment Endpoint

```python
def call_singpay_payment(
    operator,           # "airtel", "moov", "maviance"
    amount,            # Payment amount in XAF
    reference,         # Unique reference: f"GABOSHOP_{order.order_number}"
    phone,             # Client's phone number
    portefeuille=None, # Wallet ID from SINGPAY_WALLET_ID
    disbursement=None, # Disbursement ID from SINGPAY_DISBURSEMENT_ID
    is_transfer=False, # Enable transfers (SINGPAY_ENABLE_TRANSFER)
):
    # Route to correct SingPay endpoint
    if operator == "airtel":
        path = "/74/paiement"        # Airtel Money
    elif operator == "moov":
        path = "/62/paiement"        # Moov Money
    elif operator == "maviance":
        path = "/maviance/paiement"  # Maviance

    # Normalize phone and amount
    normalized_amount = _normalize_amount(amount)
    normalized_phone = _normalize_msisdn(phone)

    # Build payload
    payload = {
        "amount": normalized_amount,
        "reference": reference,
        "client_msisdn": normalized_phone,
        "portefeuille": portefeuille or SINGPAY_WALLET_ID,
        "disbursement": disbursement or SINGPAY_DISBURSEMENT_ID,
        "isTransfer": bool(is_transfer),
    }

    # Send to SingPay API
    return _singpay_request("POST", path, payload=payload)
```

### SingPay Request Headers

```python
def _singpay_headers(wallet_id=None, require_wallet=True):
    return {
        "x-client-id": SINGPAY_CLIENT_ID,
        "x-client-secret": SINGPAY_CLIENT_SECRET,
        "x-wallet": SINGPAY_WALLET_ID,
        "Content-Type": "application/json",
    }
```

### SingPay Configuration Required

**Environment Variables (.env):**
```bash
SINGPAY_BASE_URL=https://gateway.singpay.ga/v1
SINGPAY_CLIENT_ID=<SINGPAY_CLIENT_ID>
SINGPAY_CLIENT_SECRET=<SINGPAY_CLIENT_SECRET>
SINGPAY_WALLET_ID=<SINGPAY_WALLET_ID>
SINGPAY_DISBURSEMENT_ID=
SINGPAY_TIMEOUT=30
SINGPAY_ENABLE_TRANSFER=False
```

---

## 📊 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND: ClientDashboard.jsx                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. User fills form:                                            │
│     - Delivery address, phone, zone                             │
│     - Payment method (airtel_money or moov_money)               │
│     - Cart items                                                │
│                                                                  │
│  2. User clicks "Passer la commande"                            │
│                                                                  │
│  3. Build payload (WITHOUT payment_method):                     │
│     {                                                            │
│       store, city, delivery_address, delivery_phone,            │
│       delivery_zone, delivery_requested, notes, items[]         │
│     }                                                            │
│                                                                  │
│  4. POST to /api/v1/orders/create/                              │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND: OrderCreateView (api/v1/orders.py)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Validate order data                                         │
│  2. Create Order record in database                             │
│  3. Calculate delivery costs                                    │
│  4. Return { success: true, data: order }                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND: After order creation success                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Extract orderId from response                                  │
│                                                                  │
│  Call initPayment(orderId, {                                    │
│    payment_method: 'airtel_money' or 'moov_money',             │
│    phone_number: delivery_phone                                 │
│  })                                                              │
│                                                                  │
│  POST to /orders/{orderId}/payments/init/                       │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND: PaymentInitView (api/v1/payments.py)                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Validate payment_method is 'airtel_money' or 'moov_money'  │
│  2. Calculate 3% Mobile Money fees                              │
│  3. Create Payment record with status='pending'                 │
│  4. Route to PaymentService._call_operator_api()               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  PaymentService (payments/services.py)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Format phone number for Gabon                               │
│  2. Call appropriate SingPay API:                               │
│     - _call_airtel_money_api() → SingPay /74/paiement          │
│     - _call_moov_money_api() → SingPay /62/paiement            │
│  3. Parse SingPay response                                      │
│  4. Extract transaction_id and operator_reference              │
│  5. Return next_steps to frontend                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  SingPay Gateway (payments/utils.py - External API)            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  POST https://gateway.singpay.ga/v1/74/paiement               │
│                                                                  │
│  Headers:                                                       │
│  - x-client-id: SINGPAY_CLIENT_ID                              │
│  - x-client-secret: SINGPAY_CLIENT_SECRET                      │
│  - x-wallet: SINGPAY_WALLET_ID                                 │
│                                                                  │
│  Body:                                                          │
│  {                                                              │
│    "amount": 50000,                                             │
│    "reference": "GABOSHOP_12345",                              │
│    "client_msisdn": "24171234567",                             │
│    "portefeuille": "<SINGPAY_WALLET_ID>",                │
│    "disbursement": "",                                         │
│    "isTransfer": false                                         │
│  }                                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  BACKEND: Return to Frontend                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  {                                                              │
│    "success": true,                                             │
│    "data": {                                                    │
│      "payment": {                                               │
│        "id": 1,                                                 │
│        "transaction_id": "AIRTEL_12345_timestamp",             │
│        "status": "pending"                                      │
│      },                                                         │
│      "next_steps": {                                            │
│        "message": "Un prompt de paiement apparaitra...",       │
│        "singpay_status": {...}                                 │
│      }                                                          │
│    }                                                            │
│  }                                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                             ↓
┌─────────────────────────────────────────────────────────────────┐
│  FRONTEND: Display Payment Prompt to User                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Toast message:                                                 │
│  "Airel Money initialise. Verifiez votre telephone              │
│   et confirmez avec votre PIN."                                 │
│                                                                  │
│  User receives USSD prompt on their phone to confirm payment    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📝 Key Notes

### Request Body Details

**POST `/api/v1/orders/create/` - Order Creation:**
- ✅ Includes: store, city, delivery_address, delivery_phone, delivery_zone, items
- ❌ Does NOT include: payment_method (sent separately after order creation)
- ❌ Does NOT include: payment_fee (calculated by backend)

**POST `/orders/{orderId}/payments/init/` - Payment Initialization:**
- ✅ Includes: payment_method ('airtel_money' or 'moov_money')
- ✅ Includes: phone_number (for payment prompt routing)  
- ✅ Includes: operator (optional, detected from phone format)

### SingPay Operator Codes

| Operator | SingPay Path | Frontend Code | Notes |
|----------|--------------|--------------|-------|
| Airtel Money | `/74/paiement` | `airtel_money` | Sends USSD prompt to Airtel subscribers |
| Moov Money | `/62/paiement` | `moov_money` | Sends USSD prompt to Moov subscribers |
| Maviance | `/maviance/paiement` | Not yet exposed in frontend | For future expansion |

### Phone Number Formatting

The backend automatically normalizes phone numbers:
```python
def _normalize_msisdn(phone):
    return (
        str(phone)
        .strip()
        .replace(" ", "")
        .replace("-", "")
        .replace(".", "")
    )
```

Supports:
- `+241 71 234 567`
- `24171234567`
- `+241-71-234-567`
- All normalize to `24171234567`

### Amount Normalization

All amounts are converted to integers (centimes XAF):
```python
def _normalize_amount(amount):
    return int(Decimal(str(amount)).quantize(Decimal("1")))
```

Example: `50000.5` → `50000` (XAF centimes)

---

## 🔗 Related Files Summary

| File | Purpose |
|------|---------|
| [frontend/src/pages/client/ClientDashboard.jsx](frontend/src/pages/client/ClientDashboard.jsx) | Main UI for order creation & form |
| [frontend/src/services/orderService.js](frontend/src/services/orderService.js) | Order creation API call |
| [frontend/src/services/paymentService.js](frontend/src/services/paymentService.js) | Payment initialization API call |
| [api/v1/orders.py](api/v1/orders.py) | `POST /orders/create/` endpoint |
| [api/v1/payments.py](api/v1/payments.py) | `POST /orders/{id}/payments/init/` endpoint |
| [payments/services.py](payments/services.py) | PaymentService class, operator routing |
| [payments/utils.py](payments/utils.py) | SingPay API utilities & helpers |
| [.env](.env) | SingPay configuration (credentials, wallet ID) |

