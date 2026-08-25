from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from products.models import Product

class OrderStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    CANCELLED = 'CANCELLED', 'Cancelled'

class Order(models.Model):
    customer_name = models.CharField(max_length=255, help_text="Customer identifier / name")
    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING,
        db_index=True,
        help_text="Current lifecycle status of the order"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    cancelled_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when the order was cancelled")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f"Order #{self.id} - {self.customer_name} ({self.status})"

    @property
    def total_amount(self):
        return sum(item.line_total for item in self.items.all()) if self.pk else Decimal('0.00')


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Quantity of product reserved for this order"
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Snapshot of product unit price at the time of order creation"
    )

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (Order #{self.order_id})"

    @property
    def line_total(self):
        return self.quantity * self.unit_price
