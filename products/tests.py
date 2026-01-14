from django.test import TestCase
from .models import Product, ProductVariant, ProductImage, ProductCategory
from stores.models import Store, StoreCategory
from django.core.files.uploadedfile import SimpleUploadedFile
from .serializers import ProductDetailSerializer


class ProductModelTests(TestCase):
	def setUp(self):
		cat = StoreCategory.objects.create(name='Default')
		# create a manager user required by Store.manager FK
		from users.models import User
		mgr = User.objects.create_user(phone='+2419000000', password='mgrpass', user_type='store_manager')
		self.store = Store.objects.create(name='TestStore', category=cat, manager=mgr, phone='+2419000000', address='addr', city='City', zone='Zone')
		self.category = ProductCategory.objects.create(store=self.store, name='Cat1')

	def test_create_product_and_variant_serialization(self):
		p = Product.objects.create(store=self.store, category=self.category, name='Prod A', price=1000, stock=10)
		v1 = ProductVariant.objects.create(product=p, name='Red', sku='PRODA-RED', price=1100, stock=3)
		v2 = ProductVariant.objects.create(product=p, name='Blue', sku='', price=None, stock=5)

		serializer = ProductDetailSerializer(p)
		data = serializer.data

		self.assertIn('variants', data)
		self.assertEqual(len(data['variants']), 2)

	def test_product_without_sku_allowed(self):
		p = Product.objects.create(store=self.store, category=self.category, name='Prod B', price=500, stock=2, sku='')
		self.assertEqual(p.sku, '')

	def test_image_upload_and_serialization(self):
		p = Product.objects.create(store=self.store, category=self.category, name='Prod C', price=200, stock=1)
		# create a small dummy file
		image_content = b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
		f = SimpleUploadedFile('small.gif', image_content, content_type='image/gif')
		img = ProductImage.objects.create(product=p, image=f, alt_text='t1')

		serializer = ProductDetailSerializer(p)
		data = serializer.data
		self.assertIn('images', data)
		self.assertEqual(len(data['images']), 1)

	def test_pagination_simple(self):
		# create 15 products and check simple pagination using Django queryset slicing
		for i in range(15):
			Product.objects.create(store=self.store, category=self.category, name=f'P{i}', price=100+i, stock=1)

		qs = Product.objects.filter(store=self.store).order_by('-created_at')
		page1 = qs[:10]
		page2 = qs[10:20]
		self.assertEqual(len(page1), 10)
		self.assertEqual(len(page2), 5)

	def test_product_creation_requires_weight(self):
		# Ensure API-level serializer enforces weight requirement
		from .serializers import ProductCreateSerializer
		data = {
			'name': 'NoWeight',
			'category': self.category.id,
			'price': 100,
			'stock': 10
		}
		serializer = ProductCreateSerializer(data=data, context={'request': None})
		self.assertFalse(serializer.is_valid())
		self.assertIn('weight_kg', serializer.errors)
