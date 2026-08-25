from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from products.models import Product

class ProductModelTest(TestCase):
    def setUp(self):
        self.product = Product.objects.create(
            name="Laptop Stand",
            sku="STAND-001",
            description="Ergonomic aluminum stand",
            price=Decimal("49.99"),
            stock_quantity=20,
            is_active=True
        )

    def test_product_creation(self):
        self.assertEqual(str(self.product), "Laptop Stand (STAND-001)")
        self.assertEqual(self.product.price, Decimal("49.99"))
        self.assertEqual(self.product.stock_quantity, 20)
        self.assertTrue(self.product.is_active)

    def test_product_price_validation(self):
        invalid_product = Product(
            name="Free Item",
            sku="FREE-001",
            price=Decimal("0.00"),
            stock_quantity=5
        )
        with self.assertRaises(ValidationError):
            invalid_product.full_clean()

    def test_product_negative_price_validation(self):
        invalid_product = Product(
            name="Negative Price",
            sku="NEG-001",
            price=Decimal("-10.00"),
            stock_quantity=5
        )
        with self.assertRaises(ValidationError):
            invalid_product.full_clean()

    def test_product_sku_uniqueness(self):
        with self.assertRaises(IntegrityError):
            Product.objects.create(
                name="Duplicate SKU Item",
                sku="STAND-001",
                price=Decimal("19.99"),
                stock_quantity=10
            )

    def test_product_soft_delete(self):
        self.product.soft_delete()
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_active)
