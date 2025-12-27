from django.utils import timezone
from users.models import User
from stores.models import StoreCategory, Store
from products.models import Product, ProductCategory
from orders.models import Order, OrderItem
from payments.models import Payment
import time

# Manager
manager = User.objects.filter(user_type='store_manager').first()
if not manager:
    manager = User.objects.create_user(phone='+24170001000', password='pass', user_type='store_manager', email='manager@example.com')

# Client
client = User.objects.filter(user_type='client').first()
if not client:
    client = User.objects.create_user(phone='+24170002000', password='pass', user_type='client', email='client@example.com')

# StoreCategory
sc = StoreCategory.objects.first() or StoreCategory.objects.create(name='TestCat')

# Store
store = Store.objects.filter(manager=manager).first()
if not store:
    store = Store.objects.create(
        name='Demo Store',
        category=sc,
        manager=manager,
        phone='+24112345678',
        address='Demo Address',
        zone='TestZone',
        city='Libreville',
        latitude=0,
        longitude=0,
    )

# ProductCategory
pc = ProductCategory.objects.filter(store_category=sc).first()
if not pc:
    pc = ProductCategory.objects.create(store=store, store_category=sc, name='General')

# Product
product = Product.objects.filter(store=store).first()
if not product:
    product = Product.objects.create(store=store, category=pc, name='Test Product', price=1000.00, stock=100)

# Create Order
order = Order.objects.create(
    client=client,
    store=store,
    status='pending_payment',
    delivery_type='standard',
    delivery_address='1 Demo Street',
    delivery_phone=client.phone,
    delivery_zone='TestZone'
)
print('ORDER_CREATED', order.id, order.order_number)

# OrderItem
oi = OrderItem.objects.create(order=order, product=product, quantity=2, unit_price=product.price)
order.calculate_totals()
print('ORDER_TOTALS', order.items_total, order.total_amount)

# Create Payment and mark success
p = Payment.objects.create(order=order, payment_method='cash', status='success', amount=order.total_amount or order.items_total, client_phone=client.phone, completed_at=timezone.now())
print('PAYMENT_CREATED', p.id)

# Wait for celery task to run
print('Waiting 6s for assignment task...')
time.sleep(6)

try:
    from delivery.models import Delivery
    d = Delivery.objects.get(order=order)
    print('DELIVERY', d.id, d.status, 'agent_id', getattr(d.delivery_agent, 'id', None), 'assigned_at', d.assigned_at)
except Exception as e:
    print('DELIVERY_ERROR', e)
