from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemInputSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1, help_text="ID of the product to reserve")
    quantity = serializers.IntegerField(min_value=1, help_text="Quantity to reserve (must be >= 1)")


class OrderCreateSerializer(serializers.Serializer):
    customer_name = serializers.CharField(max_length=255, help_text="Customer identifier / name")
    items = OrderItemInputSerializer(many=True, allow_empty=False, help_text="List of items with product_id and quantity")

    def validate_customer_name(self, value):
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError("Customer name cannot be empty or whitespace only.")
        return stripped

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("Order must include at least one item.")
        return value


class OrderItemDetailSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_sku = serializers.CharField(source='product.sku', read_only=True)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            'id',
            'product_id',
            'product_name',
            'product_sku',
            'quantity',
            'unit_price',
            'line_total',
        ]


class OrderDetailSerializer(serializers.ModelSerializer):
    items = OrderItemDetailSerializer(many=True, read_only=True)
    total_amount = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = [
            'id',
            'customer_name',
            'status',
            'total_amount',
            'items',
            'created_at',
            'updated_at',
            'cancelled_at',
        ]
        read_only_fields = fields
