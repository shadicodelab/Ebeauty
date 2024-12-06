from django.contrib import admin
from .models import Product, CartItem, Cart, Order,User,OrderDelivery,Order

# Check if Product is already registered
if Product not in admin.site._registry:
    @admin.register(Product)
    class ProductAdmin(admin.ModelAdmin):
        list_display = ('name', 'price', 'stock')
        search_fields = ('name',)
        list_filter = ('price',)
        ordering = ('name',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'total_price')
    search_fields = ('user__username',)
    list_filter = ('created_at',)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'cart', 'quantity', 'item_total_price')
    search_fields = ('product__name',)
    list_filter = ('cart',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_price', 'status', 'created_at')
    search_fields = ('user__username', 'id')
    list_filter = ('status', 'created_at')
    ordering = ('-created_at',)            # Default ordering by most recent

class OrderDeliveryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'delivery_location', 'phone_number', 'created_at')  # Add any other fields you want
    list_filter = ('user', 'created_at')  # Add filters to narrow down results
    search_fields = ('full_name', 'user__username') 

admin.site.register(User)
admin.site.register(OrderDelivery)

# Customizing the admin site header
admin.site.site_header = "E-Commerce Admin Panel"

