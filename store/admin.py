from django.contrib import admin
from .models import Product, Order, OrderItem


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'total_amount', 'created_at', 'stripe_session_id']
    list_filter = ['status', 'created_at']
    readonly_fields = ['stripe_session_id', 'stripe_payment_intent_id', 'created_at', 'updated_at', 'idempotency_key']
    inlines = [OrderItemInline]
    
    def has_add_permission(self, request):
        return False  # Orders should only be created through the payment flow

