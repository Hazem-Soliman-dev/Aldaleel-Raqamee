from django.contrib import admin
from django.contrib import messages
from .models import Order, OrderItem
from .services import OrderService

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price', 'line_total')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'status', 'total_amount', 'created_at', 'approved_at', 'rejected_at', 'cancelled_at')
    list_filter = ('status', 'created_at')
    search_fields = ('customer_name', 'id')
    readonly_fields = ('created_at', 'updated_at', 'approved_at', 'rejected_at', 'cancelled_at', 'total_amount')
    inlines = [OrderItemInline]
    actions = ['approve_selected_orders', 'reject_selected_orders']

    @admin.action(description="Approve selected PENDING orders")
    def approve_selected_orders(self, request, queryset):
        success_count = 0
        error_count = 0
        for order in queryset:
            try:
                OrderService.approve_order(order.id)
                success_count += 1
            except Exception as e:
                error_count += 1
        if success_count:
            self.message_user(request, f"Successfully approved {success_count} order(s).", messages.SUCCESS)
        if error_count:
            self.message_user(request, f"Failed to approve {error_count} order(s) (only PENDING orders can be approved).", messages.WARNING)

    @admin.action(description="Reject selected PENDING orders (releases stock)")
    def reject_selected_orders(self, request, queryset):
        success_count = 0
        error_count = 0
        for order in queryset:
            try:
                OrderService.reject_order(order.id)
                success_count += 1
            except Exception as e:
                error_count += 1
        if success_count:
            self.message_user(request, f"Successfully rejected {success_count} order(s) and restored reserved stock.", messages.SUCCESS)
        if error_count:
            self.message_user(request, f"Failed to reject {error_count} order(s) (only PENDING orders can be rejected).", messages.WARNING)
