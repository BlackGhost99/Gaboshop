from django.test import TestCase
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile
from users.models import User
from stores.models import Store, StoreCategory
from .models import Product, ProductCategory


class ProductAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # manager user
        self.mgr = User.objects.create_user(phone='+2419000100', password='mgrpass', user_type='store_manager')
        self.cat = StoreCategory.objects.create(name='Default')
        self.store = Store.objects.create(name='APITestStore', category=self.cat, manager=self.mgr, phone='+2419000100', address='addr', city='City', zone='Zone')
        self.product_category = ProductCategory.objects.create(store=self.store, name='PCat')

    def test_create_product_via_api(self):
        self.client.force_authenticate(user=self.mgr)
    url = '/api/v1/products-api/'
        payload = {
            'name': 'API Prod',
            'price': '1500.00',
            'stock': 5,
            'category': self.product_category.id,
            'store': self.store.id
        }
        r = self.client.post(url, payload, format='json')
        self.assertEqual(r.status_code, 201)
        self.assertIn('id', r.data)

    def test_search_and_list(self):
        # create several products
        for i in range(5):
            Product.objects.create(store=self.store, category=self.product_category, name=f'Apple {i}', price=100+i, stock=1)
        for i in range(3):
            Product.objects.create(store=self.store, category=self.product_category, name=f'Banana {i}', price=50+i, stock=1)

    url = '/api/v1/products-api/?q=Apple'
        self.client.force_authenticate(user=self.mgr)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        # Expect only Apple matches
        results = r.data.get('results') if isinstance(r.data, dict) else r.data
        # results may be a list or paginated dict
        if isinstance(results, list):
            self.assertEqual(len(results), 5)
        else:
            self.assertEqual(results.get('count'), 5)

    def test_upload_image_endpoint(self):
        p = Product.objects.create(store=self.store, category=self.product_category, name='WithImage', price=200, stock=1)
        self.client.force_authenticate(user=self.mgr)
    url = f'/api/v1/products-api/{p.id}/upload-image/'
        image_content = b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00"
        f = SimpleUploadedFile('test.gif', image_content, content_type='image/gif')
        r = self.client.post(url, {'image': f, 'alt_text': 'api'}, format='multipart')
        self.assertEqual(r.status_code, 201)
        self.assertIn('image', r.data)
