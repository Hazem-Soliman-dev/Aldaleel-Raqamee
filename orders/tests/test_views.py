from decimal import Decimal
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from products.models import Product
from orders.models import Order, OrderItem, OrderStatus

class OrderAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.p1 = Product.objects.create(
            name="Laptop",
            sku="LAP-001",
            price=Decimal("1000.00"),
            stock_quantity=10,
            is_active=True
        )
        self.p2 = Product.objects.create(
            name="Headphones",
            sku="AUD-002",
            price=Decimal("150.00"),
            stock_quantity=5,
            is_active=True
        )
        self.p_inactive = Product.objects.create(
            name="Deprecated Item",
            sku="DEP-003",
            price=Decimal("20.00"),
            stock_quantity=10,
            is_active=False
        )

    def test_create_order_success_reserves_stock(self):
        payload = {
            "customer_name": "Bob",
            "items": [
                {"product_id": self.p1.id, "quantity": 3},
                {"product_id": self.p2.id, "quantity": 2}
            ]
        }
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['customer_name'], "Bob")
        self.assertEqual(response.data['status'], "PENDING")
        self.assertEqual(len(response.data['items']), 2)
        self.assertEqual(Decimal(str(response.data['total_amount'])), Decimal("3300.00"))

        # Verify stock decremented
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 7)
        self.assertEqual(self.p2.stock_quantity, 3)

    def test_create_order_insufficient_stock_returns_409(self):
        payload = {
            "customer_name": "Charlie",
            "items": [
                {"product_id": self.p1.id, "quantity": 15}
            ]
        }
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("Insufficient stock", str(response.data))

        # Verify stock untouched
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 10)
        self.assertEqual(Order.objects.count(), 0)

    def test_create_order_atomic_rollback_on_partial_failure(self):
        # p1 has 10 (requesting 4 is valid), p2 has 5 (requesting 8 is INVALID)
        payload = {
            "customer_name": "David",
            "items": [
                {"product_id": self.p1.id, "quantity": 4},
                {"product_id": self.p2.id, "quantity": 8}
            ]
        }
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        # Confirm TASK-011: Neither product's stock was decremented!
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 10)
        self.assertEqual(self.p2.stock_quantity, 5)
        self.assertEqual(Order.objects.count(), 0)
        self.assertEqual(OrderItem.objects.count(), 0)

    def test_create_order_empty_items_rejected(self):
        payload = {
            "customer_name": "Eve",
            "items": []
        }
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_zero_quantity_rejected(self):
        payload = {
            "customer_name": "Frank",
            "items": [{"product_id": self.p1.id, "quantity": 0}]
        }
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_nonexistent_product_rejected(self):
        payload = {
            "customer_name": "Grace",
            "items": [{"product_id": 99999, "quantity": 1}]
        }
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_order_inactive_product_rejected(self):
        payload = {
            "customer_name": "Helen",
            "items": [{"product_id": self.p_inactive.id, "quantity": 1}]
        }
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cancel_pending_order_restores_stock(self):
        # Create order reserving 3 units of p1
        payload = {
            "customer_name": "Ivan",
            "items": [{"product_id": self.p1.id, "quantity": 3}]
        }
        res_create = self.client.post('/api/orders/', payload, format='json')
        order_id = res_create.data['id']
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 7)

        # Cancel order
        res_cancel = self.client.post(f'/api/orders/{order_id}/cancel/')
        self.assertEqual(res_cancel.status_code, status.HTTP_200_OK)
        self.assertEqual(res_cancel.data['status'], "CANCELLED")
        self.assertIsNotNone(res_cancel.data['cancelled_at'])

        # Check stock restored to original 10
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 10)

    def test_cancel_already_cancelled_order_returns_409_and_prevents_double_release(self):
        # Reserve 4 units
        payload = {
            "customer_name": "Julia",
            "items": [{"product_id": self.p1.id, "quantity": 4}]
        }
        res_create = self.client.post('/api/orders/', payload, format='json')
        order_id = res_create.data['id']

        # Cancel once -> OK
        res_cancel1 = self.client.post(f'/api/orders/{order_id}/cancel/')
        self.assertEqual(res_cancel1.status_code, status.HTTP_200_OK)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 10)

        # Cancel again -> 409 Conflict (TASK-014, TASK-015)
        res_cancel2 = self.client.post(f'/api/orders/{order_id}/cancel/')
        self.assertEqual(res_cancel2.status_code, status.HTTP_409_CONFLICT)

        # Ensure stock is NOT increased above 10
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 10)

    def test_cancel_nonexistent_order_returns_404(self):
        response = self.client.post('/api/orders/99999/cancel/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_and_retrieve_orders(self):
        self.client.post('/api/orders/', {
            "customer_name": "Kevin",
            "items": [{"product_id": self.p1.id, "quantity": 1}]
        }, format='json')

        res_list = self.client.get('/api/orders/')
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        self.assertEqual(res_list.data['count'], 1)

        order_id = res_list.data['results'][0]['id']
        res_detail = self.client.get(f'/api/orders/{order_id}/')
        self.assertEqual(res_detail.status_code, status.HTTP_200_OK)
        self.assertEqual(res_detail.data['customer_name'], "Kevin")
