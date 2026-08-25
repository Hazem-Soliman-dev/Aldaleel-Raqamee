from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'quantity', 'unit_price', 'line_total')
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer_name', 'status', 'total_amount', 'created_at', 'cancelled_at')
    list_filter = ('status', 'created_at')
    search_fields = ('customer_name', 'id')
    readonly_fields = ('created_at', 'updated_at', 'cancelled_at', 'total_amount')
    inlines = [OrderItemInline]
