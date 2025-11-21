from django.contrib import admin
from .models import Category, Product, ProductImage, Order, OrderItem

# -------------------------------
# Category Admin
# -------------------------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "parent", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

# -------------------------------
# Product Image Inline
# -------------------------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1

# -------------------------------
# Product Admin
# -------------------------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "category", "price", "discount_price", "stock", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("name", "sku", "description")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [ProductImageInline]

# -------------------------------
# Order Item Inline
# -------------------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "quantity", "price")
    can_delete = False

# -------------------------------
# Order Admin
# -------------------------------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'full_name', 'created_at', 'is_paid')
    list_filter = ('is_paid', 'created_at')
    search_fields = ('user__username', 'full_name', 'email', 'city')
    ordering = ('-created_at',)
    inlines = [OrderItemInline]

    def total_items(self, obj):
        return obj.items.count()
    total_items.short_description = "Total Items"
