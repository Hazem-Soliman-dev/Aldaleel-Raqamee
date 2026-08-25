import time
import concurrent.futures
from decimal import Decimal
from django.test import TransactionTestCase
from django.db import connection
from django.db.utils import OperationalError
from rest_framework import status
from rest_framework.test import APIClient
from products.models import Product
from orders.models import Order, OrderStatus
from orders.services import OrderService

class ConcurrencyTest(TransactionTestCase):
    """
    Concurrency and race condition tests (TASK-010, TASK-009, TASK-014).
    Uses TransactionTestCase to allow real database commits.
    Tests atomic reservation under high concurrency, zero overselling,
    and prevention of double stock release.
    """
    reset_sequences = True

    def setUp(self):
        self.product = Product.objects.create(
            name="Limited Edition Sneaker",
            sku="SNK-001",
            price=Decimal("199.99"),
            stock_quantity=3,  # Only 3 units available
            is_active=True
        )

    def tearDown(self):
        connection.close()

    def _attempt_order(self, customer_id):
        client = APIClient()
        response = client.post('/api/orders/', {
            "customer_name": f"Customer-{customer_id}",
            "items": [{"product_id": self.product.id, "quantity": 1}]
        }, format='json')
        connection.close()
        return response.status_code

    def test_concurrent_order_reservations_prevent_overselling(self):
        """
        Simulate near-simultaneous customer requests competing for limited stock (TASK-010, TASK-009).
        Asserts that no more than available stock is reserved (never oversold, never negative stock).
        """
        num_requests = 6
        if connection.vendor == 'sqlite':
            # On SQLite (which ignores select_for_update and uses DB-level locking),
            # execute rapid near-simultaneous requests in sequence or with thread barrier
            results = [self._attempt_order(i) for i in range(num_requests)]
        else:
            # On PostgreSQL, execute truly concurrent threads utilizing row-level locks (select_for_update)
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
                futures = [
                    executor.submit(self._attempt_order, i)
                    for i in range(num_requests)
                ]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

        success_count = results.count(status.HTTP_201_CREATED)
        conflict_count = results.count(status.HTTP_409_CONFLICT)

        self.assertEqual(
            success_count, 3,
            f"Expected exactly 3 successful reservations, got {success_count}. All results: {results}"
        )
        self.assertEqual(
            conflict_count, 3,
            f"Expected 3 conflicts due to depleted stock, got {conflict_count}. All results: {results}"
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 0, "Stock should be exactly 0, never negative.")
        self.assertEqual(Order.objects.filter(status=OrderStatus.PENDING).count(), 3)

    def _attempt_cancel(self, order_id):
        client = APIClient()
        response = client.post(f'/api/orders/{order_id}/cancel/')
        connection.close()
        return response.status_code

    def test_concurrent_order_cancellations_prevent_double_release(self):
        """
        Simulate multiple cancellation requests on the same order (TASK-014, TASK-015).
        Asserts exactly 1 succeeds (200 OK), all subsequent/competing fail with 409 Conflict,
        and stock is restored exactly once.
        """
        # Create an order reserving 2 units
        order = OrderService.create_order("Customer-ConCancel", [{"product_id": self.product.id, "quantity": 2}])
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 1)

        num_requests = 4
        if connection.vendor == 'sqlite':
            results = [self._attempt_cancel(order.id) for _ in range(num_requests)]
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_requests) as executor:
                futures = [
                    executor.submit(self._attempt_cancel, order.id)
                    for _ in range(num_requests)
                ]
                results = [f.result() for f in concurrent.futures.as_completed(futures)]

        success_count = results.count(status.HTTP_200_OK)
        conflict_count = results.count(status.HTTP_409_CONFLICT)

        self.assertEqual(
            success_count, 1,
            f"Expected exactly 1 cancellation to succeed, got {success_count}. All results: {results}"
        )
        self.assertEqual(
            conflict_count, 3,
            f"Expected 3 conflicts for already-cancelled order, got {conflict_count}. All results: {results}"
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3, "Stock should be restored back to original 3, not more.")
