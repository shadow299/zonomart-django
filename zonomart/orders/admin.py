from django.contrib import admin
from .models import Payment, Order, OrderProduct

# Register your models here.

class OrderProductInline(admin.TabularInline):
    model = OrderProduct
    readonly_fields = ['payment', 'user', 'product', 'quantity', 'product_price', 'ordered', 'variations']
    extra = 0

class orderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'phone', 'email', 'city', 'order_total', 'tax', 'status', 'ip', 'created_at']
    list_filter = ['status', 'is_ordered']
    search_fields = ['order_number', 'first_name', 'last_name', 'phone', 'email']
    inlines = [OrderProductInline]

admin.site.register(Payment)
admin.site.register(Order, orderAdmin)
admin.site.register(OrderProduct)
