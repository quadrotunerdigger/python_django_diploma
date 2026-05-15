from django.contrib import admin
from .models import (
    Profile,
    Category,
    Tag,
    Product,
    ProductImage,
    Specification,
    Review,
    Sale,
    Order,
    OrderItem,
    SiteSettings,
)


# ─── Inlines ────────────────────────────────


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


class SpecificationInline(admin.TabularInline):
    model = Specification
    extra = 1


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    readonly_fields = ("author", "email", "text", "rate", "date")


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


# ─── Soft delete mixin for admin ────────────


class SoftDeleteAdmin(admin.ModelAdmin):
    """Admin that uses all_objects (including soft-deleted) and adds soft-delete actions."""

    def get_queryset(self, request):
        return self.model.all_objects.all()

    actions = ["soft_delete_selected", "restore_selected"]

    @admin.action(description="Мягкое удаление выбранных")
    def soft_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.soft_delete()

    @admin.action(description="Восстановить выбранные")
    def restore_selected(self, request, queryset):
        for obj in queryset:
            obj.restore()


# ─── Model admins ───────────────────────────


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "full_name", "phone")
    search_fields = ("full_name", "phone", "user__username")


@admin.register(Category)
class CategoryAdmin(SoftDeleteAdmin):
    list_display = ("title", "parent", "is_active", "sort_index", "is_deleted")
    list_filter = ("is_active", "is_deleted", "parent")
    search_fields = ("title",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(SoftDeleteAdmin):
    list_display = (
        "title",
        "category",
        "price",
        "count",
        "rating",
        "limited_edition",
        "is_deleted",
    )
    list_filter = ("category", "free_delivery", "limited_edition", "is_deleted")
    search_fields = ("title", "description")
    inlines = [ProductImageInline, SpecificationInline, ReviewInline]
    filter_horizontal = ("tags",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "author", "rate", "date")
    list_filter = ("rate",)
    search_fields = ("author", "text")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ("product", "sale_price", "date_from", "date_to")
    list_filter = ("date_from", "date_to")


@admin.register(Order)
class OrderAdmin(SoftDeleteAdmin):
    list_display = (
        "id",
        "full_name",
        "status",
        "total_cost",
        "delivery_type",
        "payment_type",
        "created_at",
        "is_deleted",
    )
    list_filter = ("status", "delivery_type", "payment_type", "is_deleted")
    search_fields = ("full_name", "email", "phone")
    inlines = [OrderItemInline]


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = (
        "express_delivery_cost",
        "ordinary_delivery_cost",
        "free_delivery_threshold",
    )

    def has_add_permission(self, request):
        # Singleton — only one record
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
