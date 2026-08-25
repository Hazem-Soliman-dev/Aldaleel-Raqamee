from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from products.models import Product
from orders.models import Order, OrderItem, OrderStatus
from orders.services import OrderService

User = get_user_model()

class OrderAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_superuser(username='testadmin', email='a@t.com', password='p')
        self.customer1 = User.objects.create_user(username='alice', email='alice@t.com', password='p')
        self.customer2 = User.objects.create_user(username='bob', email='bob@t.com', password='p')

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

    def test_customer_only_sees_own_orders(self):
        # Alice creates an order
        self.client.force_authenticate(user=self.customer1)
        self.client.post('/api/orders/', {
            "items": [{"product_id": self.p1.id, "quantity": 1}]
        }, format='json')

        # Bob creates an order
        self.client.force_authenticate(user=self.customer2)
        self.client.post('/api/orders/', {
            "items": [{"product_id": self.p1.id, "quantity": 1}]
        }, format='json')

        # When logged in as Bob, only 1 order (Bob's) is visible
        res_bob = self.client.get('/api/orders/')
        self.assertEqual(res_bob.status_code, status.HTTP_200_OK)
        self.assertEqual(res_bob.data['count'], 1)
        self.assertEqual(res_bob.data['results'][0]['customer_name'], 'bob')

        # When logged in as Alice, only 1 order (Alice's) is visible
        self.client.force_authenticate(user=self.customer1)
        res_alice = self.client.get('/api/orders/')
        self.assertEqual(res_alice.status_code, status.HTTP_200_OK)
        self.assertEqual(res_alice.data['count'], 1)
        self.assertEqual(res_alice.data['results'][0]['customer_name'], 'alice')

        # When logged in as Admin, ALL orders are visible
        self.client.force_authenticate(user=self.admin_user)
        res_admin = self.client.get('/api/orders/')
        self.assertEqual(res_admin.status_code, status.HTTP_200_OK)
        self.assertEqual(res_admin.data['count'], 2)

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

        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 10)
        self.assertEqual(Order.objects.count(), 0)

    def test_create_order_atomic_rollback_on_partial_failure(self):
        payload = {
            "customer_name": "David",
            "items": [
                {"product_id": self.p1.id, "quantity": 4},
                {"product_id": self.p2.id, "quantity": 8}
            ]
        }
        response = self.client.post('/api/orders/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 10)
        self.assertEqual(self.p2.stock_quantity, 5)
        self.assertEqual(Order.objects.count(), 0)

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
        payload = {
            "customer_name": "Ivan",
            "items": [{"product_id": self.p1.id, "quantity": 3}]
        }
        res_create = self.client.post('/api/orders/', payload, format='json')
        order_id = res_create.data['id']
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 7)

        res_cancel = self.client.post(f'/api/orders/{order_id}/cancel/')
        self.assertEqual(res_cancel.status_code, status.HTTP_200_OK)
        self.assertEqual(res_cancel.data['status'], "CANCELLED")
        self.assertIsNotNone(res_cancel.data['cancelled_at'])

        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 10)

    def test_cancel_already_cancelled_order_returns_409_and_prevents_double_release(self):
        payload = {
            "customer_name": "Julia",
            "items": [{"product_id": self.p1.id, "quantity": 4}]
        }
        res_create = self.client.post('/api/orders/', payload, format='json')
        order_id = res_create.data['id']

        res_cancel1 = self.client.post(f'/api/orders/{order_id}/cancel/')
        self.assertEqual(res_cancel1.status_code, status.HTTP_200_OK)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 10)

        res_cancel2 = self.client.post(f'/api/orders/{order_id}/cancel/')
        self.assertEqual(res_cancel2.status_code, status.HTTP_409_CONFLICT)

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

    def test_shop_view_and_logout(self):
        # Anonymous user visit
        res_anon = self.client.get('/shop/')
        self.assertEqual(res_anon.status_code, status.HTTP_200_OK)
        self.assertContains(res_anon, 'Log in')

        # Authenticated user visit
        self.client.force_login(self.customer1)
        res_auth = self.client.get('/shop/')
        self.assertEqual(res_auth.status_code, status.HTTP_200_OK)
        self.assertContains(res_auth, 'Log out')
        self.assertContains(res_auth, 'csrfmiddlewaretoken')

        # Logout via POST
        res_logout = self.client.post('/api-auth/logout/?next=/shop/')
        self.assertEqual(res_logout.status_code, status.HTTP_302_FOUND)
        self.assertEqual(res_logout.headers.get('Location'), '/shop/')

    def test_admin_can_approve_pending_order(self):
        order = OrderService.create_order("CustomerA", [{"product_id": self.p1.id, "quantity": 2}])
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 8)

        # Non-staff customer attempt fails with 403
        self.client.force_authenticate(user=self.customer1)
        res_fail = self.client.post(f'/api/orders/{order.id}/approve/')
        self.assertEqual(res_fail.status_code, status.HTTP_403_FORBIDDEN)

        # Admin approve succeeds
        self.client.force_authenticate(user=self.admin_user)
        res_ok = self.client.post(f'/api/orders/{order.id}/approve/')
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        self.assertEqual(res_ok.data['status'], 'APPROVED')
        self.assertIsNotNone(res_ok.data['approved_at'])

        # Stock remains reserved
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 8)

    def test_admin_can_reject_pending_order_restores_stock(self):
        order = OrderService.create_order("CustomerB", [{"product_id": self.p1.id, "quantity": 3}])
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 7)

        # Non-staff customer attempt fails with 403
        self.client.force_authenticate(user=self.customer1)
        res_fail = self.client.post(f'/api/orders/{order.id}/reject/')
        self.assertEqual(res_fail.status_code, status.HTTP_403_FORBIDDEN)

        # Admin reject succeeds & restores stock
        self.client.force_authenticate(user=self.admin_user)
        res_ok = self.client.post(f'/api/orders/{order.id}/reject/')
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        self.assertEqual(res_ok.data['status'], 'REJECTED')
        self.assertIsNotNone(res_ok.data['rejected_at'])

        # Stock restored
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock_quantity, 10)

    def test_approve_or_reject_non_pending_order_returns_409(self):
        order = OrderService.create_order("CustomerC", [{"product_id": self.p1.id, "quantity": 1}])
        self.client.force_authenticate(user=self.admin_user)

        # Approve once
        res_app = self.client.post(f'/api/orders/{order.id}/approve/')
        self.assertEqual(res_app.status_code, status.HTTP_200_OK)

        # Re-approve returns 409
        res_app2 = self.client.post(f'/api/orders/{order.id}/approve/')
        self.assertEqual(res_app2.status_code, status.HTTP_409_CONFLICT)

        # Reject approved order returns 409
        res_rej = self.client.post(f'/api/orders/{order.id}/reject/')
        self.assertEqual(res_rej.status_code, status.HTTP_409_CONFLICT)


