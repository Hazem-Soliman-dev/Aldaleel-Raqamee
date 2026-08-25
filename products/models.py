from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError

class Product(models.Model):
    name = models.CharField(max_length=255, help_text="Product name")
    sku = models.CharField(max_length=100, unique=True, db_index=True, help_text="Unique Stock Keeping Unit")
    description = models.TextField(blank=True, default="", help_text="Product description")
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Product price in currency units. Must be greater than 0."
    )
    stock_quantity = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Available stock quantity. Must be 0 or greater."
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Designates whether this product is active (soft-delete flag)."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Product'
        verbose_name_plural = 'Products'

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def clean(self):
        super().clean()
        if self.price is not None and self.price <= Decimal('0.00'):
            raise ValidationError({'price': 'Price must be greater than 0.'})
        if self.stock_quantity is not None and self.stock_quantity < 0:
            raise ValidationError({'stock_quantity': 'Stock quantity cannot be negative.'})

    def soft_delete(self):
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])
