from decimal import Decimal
from django.test import TestCase
from products.models import Product
from orders.models import Order, OrderItem, OrderStatus

class OrderModelTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Gaming Monitor",
            sku="MON-001",
            price=Decimal("299.99"),
            stock_quantity=10
        )
        self.order = Order.objects.create(
            customer_name="Alice Smith",
            status=OrderStatus.PENDING
        )
        self.item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            unit_price=Decimal("299.99")
        )

    def test_order_and_item_properties(self):
        self.assertEqual(self.item.line_total, Decimal("599.98"))
        self.assertEqual(self.order.total_amount, Decimal("599.98"))
        self.assertIn("Alice Smith", str(self.order))
        self.assertIn("Gaming Monitor", str(self.item))
