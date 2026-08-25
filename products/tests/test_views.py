from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from products.models import Product

User = get_user_model()

class ProductAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(
            username='testadmin',
            email='admin@test.com',
            password='pass'
        )
        self.customer_user = User.objects.create_user(
            username='testcustomer',
            email='customer@test.com',
            password='pass'
        )

        self.p1 = Product.objects.create(
            name="Mechanical Keyboard",
            sku="KEY-001",
            description="RGB mechanical keyboard",
            price=Decimal("99.99"),
            stock_quantity=15,
            is_active=True
        )
        self.p2 = Product.objects.create(
            name="Wireless Mouse",
            sku="MOUSE-002",
            description="Ergonomic mouse",
            price=Decimal("39.99"),
            stock_quantity=30,
            is_active=True
        )
        self.p3_inactive = Product.objects.create(
            name="Discontinued Cable",
            sku="CBL-003",
            description="Old cable",
            price=Decimal("9.99"),
            stock_quantity=0,
            is_active=False
        )

    def test_customer_only_sees_active_products(self):
        # Customers & anonymous users only see active products (p1 and p2)
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        skus = [p['sku'] for p in response.data['results']]
        self.assertIn('KEY-001', skus)
        self.assertIn('MOUSE-002', skus)
        self.assertNotIn('CBL-003', skus)

    def test_admin_sees_all_products(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/products/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 3)

    def test_list_products_custom_page_size(self):
        response = self.client.get('/api/products/?page_size=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_search_products_by_name(self):
        response = self.client.get('/api/products/?search=Keyboard')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['sku'], 'KEY-001')

    def test_search_products_by_sku(self):
        response = self.client.get('/api/products/?search=MOUSE-002')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Wireless Mouse')

    def test_retrieve_active_product(self):
        response = self.client.get(f'/api/products/{self.p1.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sku'], 'KEY-001')
        self.assertEqual(response.data['stock_quantity'], 15)

    def test_customer_cannot_retrieve_inactive_product(self):
        # Inactive product returns 404 for customers
        response = self.client.get(f'/api/products/{self.p3_inactive.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_retrieve_inactive_product(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(f'/api/products/{self.p3_inactive.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['sku'], 'CBL-003')

    def test_admin_can_create_product(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "USB-C Hub",
            "sku": "HUB-004",
            "description": "Multiport adapter",
            "price": "45.50",
            "stock_quantity": 25,
            "is_active": True
        }
        response = self.client.post('/api/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['sku'], "HUB-004")
        self.assertTrue(Product.objects.filter(sku="HUB-004").exists())

    def test_customer_cannot_create_product_returns_403(self):
        self.client.force_authenticate(user=self.customer_user)
        payload = {
            "name": "Unauthorized Item",
            "sku": "UNAUTH-001",
            "price": "19.99",
            "stock_quantity": 10
        }
        response = self.client.post('/api/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_cannot_create_product_returns_403(self):
        payload = {
            "name": "Anon Item",
            "sku": "ANON-001",
            "price": "19.99",
            "stock_quantity": 10
        }
        response = self.client.post('/api/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_product_invalid_price_rejected(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "Zero Price Item",
            "sku": "ZERO-001",
            "price": "0.00",
            "stock_quantity": 10
        }
        response = self.client.post('/api/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('price', response.data)

    def test_create_product_negative_stock_rejected(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "Negative Stock Item",
            "sku": "NEG-002",
            "price": "19.99",
            "stock_quantity": -5
        }
        response = self.client.post('/api/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('stock_quantity', response.data)

    def test_create_product_duplicate_sku_rejected(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "name": "Another Keyboard",
            "sku": "KEY-001",
            "price": "120.00",
            "stock_quantity": 5
        }
        response = self.client.post('/api/products/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('sku', response.data)

    def test_admin_can_update_product(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {"price": "89.99", "stock_quantity": 20}
        response = self.client.patch(f'/api/products/{self.p1.id}/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.price, Decimal("89.99"))
        self.assertEqual(self.p1.stock_quantity, 20)

    def test_customer_cannot_update_product_returns_403(self):
        self.client.force_authenticate(user=self.customer_user)
        payload = {"price": "1.99"}
        response = self.client.patch(f'/api/products/{self.p1.id}/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_soft_delete_product(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f'/api/products/{self.p1.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.p1.refresh_from_db()
        self.assertFalse(self.p1.is_active)

    def test_customer_cannot_delete_product_returns_403(self):
        self.client.force_authenticate(user=self.customer_user)
        response = self.client.delete(f'/api/products/{self.p1.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
