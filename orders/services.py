from collections import defaultdict
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.http import Http404
from rest_framework import serializers

from common.exceptions import InsufficientStockException, InvalidOrderStateException
from products.models import Product
from .models import Order, OrderItem, OrderStatus

class OrderService:
    """
    Business logic service for atomic order creation, stock reservation, and order cancellation.
    Enforces ACID guarantees with row-level locks (select_for_update) and deadlock prevention.
    """

    @classmethod
    def create_order(cls, customer_name: str, items_data: list[dict]) -> Order:
        """
        Atomically reserves stock and creates an order with its line items.

        - US-002 / TASK-005, TASK-006: Create order + items
        - TASK-007, TASK-008: Validate and reserve stock
        - TASK-009: Prevent negative stock
        - TASK-010: Handle concurrent requests safely with select_for_update
        - TASK-011: Rollback failed operations completely if any item fails
        """
        if not items_data:
            raise serializers.ValidationError({"items": "Order must contain at least one item."})

        customer_name = customer_name.strip()
        if not customer_name:
            raise serializers.ValidationError({"customer_name": "Customer name cannot be empty."})

        # Consolidate requested quantities per product
        consolidated = defaultdict(int)
        for item in items_data:
            pid = item['product_id']
            qty = item['quantity']
            if qty <= 0:
                raise serializers.ValidationError({"items": f"Item quantity must be greater than 0 for product ID {pid}."})
            consolidated[pid] += qty

        # Sort product IDs to ensure a deterministic lock acquisition order and prevent deadlocks
        sorted_product_ids = sorted(consolidated.keys())

        with transaction.atomic():
            # Acquire row-level locks on requested products
            products_qs = Product.objects.select_for_update().filter(id__in=sorted_product_ids)
            product_map = {p.id: p for p in products_qs}

            # Check that all products exist
            for pid in sorted_product_ids:
                if pid not in product_map:
                    raise serializers.ValidationError({"items": f"Product with ID {pid} was not found."})

            # Check that all products are active
            for pid, product in product_map.items():
                if not product.is_active:
                    raise serializers.ValidationError({
                        "items": f"Product '{product.name}' (SKU: {product.sku}) is inactive and cannot be ordered."
                    })

            # Validate stock availability for all items before making any modifications
            for pid, required_qty in consolidated.items():
                product = product_map[pid]
                if product.stock_quantity < required_qty:
                    # TASK-009, TASK-011: Insufficient stock raises 409 Conflict and rolls back transaction
                    raise InsufficientStockException(
                        product_id=product.id,
                        sku=product.sku,
                        requested=required_qty,
                        available=product.stock_quantity
                    )

            # Deduct stock for all products
            for pid, required_qty in consolidated.items():
                product = product_map[pid]
                product.stock_quantity -= required_qty
                product.save(update_fields=['stock_quantity', 'updated_at'])

            # Create the order record with PENDING status
            order = Order.objects.create(
                customer_name=customer_name,
                status=OrderStatus.PENDING
            )

            # Create order item records with unit_price snapshots
            order_items = [
                OrderItem(
                    order=order,
                    product=product_map[item['product_id']],
                    quantity=item['quantity'],
                    unit_price=product_map[item['product_id']].price
                )
                for item in items_data
            ]
            OrderItem.objects.bulk_create(order_items)

            return order

    @classmethod
    def approve_order(cls, order_id: int) -> Order:
        """
        Atomically approves a PENDING order by an administrator.
        The reserved stock remains finalized.
        """
        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(id=order_id)
            except Order.DoesNotExist:
                raise Http404(f"Order #{order_id} not found.")

            if order.status != OrderStatus.PENDING:
                raise InvalidOrderStateException(
                    f"Order #{order_id} cannot be approved because its current status is '{order.status}'. "
                    f"Only orders in 'PENDING' status can be approved."
                )

            order.status = OrderStatus.APPROVED
            order.approved_at = timezone.now()
            order.save(update_fields=['status', 'approved_at', 'updated_at'])
            return order

    @classmethod
    def reject_order(cls, order_id: int) -> Order:
        """
        Atomically rejects a PENDING order by an administrator and restores reserved stock.
        """
        with transaction.atomic():
            try:
                order = Order.objects.select_for_update().get(id=order_id)
            except Order.DoesNotExist:
                raise Http404(f"Order #{order_id} not found.")

            if order.status != OrderStatus.PENDING:
                raise InvalidOrderStateException(
                    f"Order #{order_id} cannot be rejected because its current status is '{order.status}'. "
                    f"Only orders in 'PENDING' status can be rejected."
                )

            # Retrieve order items and lock products in deterministic ID order
            items = list(order.items.select_related('product').all())
            product_ids = sorted({item.product_id for item in items})
            products_qs = Product.objects.select_for_update().filter(id__in=product_ids)
            product_map = {p.id: p for p in products_qs}

            # Restore reserved quantities back to product stock
            for item in items:
                product = product_map.get(item.product_id)
                if product:
                    product.stock_quantity += item.quantity
                    product.save(update_fields=['stock_quantity', 'updated_at'])

            # Mark order as rejected
            order.status = OrderStatus.REJECTED
            order.rejected_at = timezone.now()
            order.save(update_fields=['status', 'rejected_at', 'updated_at'])

            return order

    @classmethod
    def cancel_order(cls, order_id: int) -> Order:
        """
        Atomically cancels a PENDING order and restores reserved stock.

        - US-003 / TASK-012: Cancel order
        - TASK-013: Restore stock
        - TASK-014: Prevent double release
        - TASK-015: Handle invalid state transitions (409 Conflict if not PENDING)
        """
        with transaction.atomic():
            try:
                # Lock order row
                order = Order.objects.select_for_update().get(id=order_id)
            except Order.DoesNotExist:
                raise Http404(f"Order #{order_id} not found.")

            # Reject invalid state transitions and double release
            if order.status != OrderStatus.PENDING:
                raise InvalidOrderStateException(
                    f"Order #{order_id} cannot be cancelled because its current status is '{order.status}'. "
                    f"Only orders in 'PENDING' status can be cancelled."
                )

            # Retrieve order items and lock products in deterministic ID order
            items = list(order.items.select_related('product').all())
            product_ids = sorted({item.product_id for item in items})
            products_qs = Product.objects.select_for_update().filter(id__in=product_ids)
            product_map = {p.id: p for p in products_qs}

            # Restore reserved quantities back to product stock
            for item in items:
                product = product_map.get(item.product_id)
                if product:
                    product.stock_quantity += item.quantity
                    product.save(update_fields=['stock_quantity', 'updated_at'])

            # Mark order as cancelled
            order.status = OrderStatus.CANCELLED
            order.cancelled_at = timezone.now()
            order.save(update_fields=['status', 'cancelled_at', 'updated_at'])

            return order
