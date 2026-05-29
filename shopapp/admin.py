"""
Конфигурация административного раздела Django для приложения shopapp.

Регистрирует все модели в Django Admin с настройками отображения,
фильтрации, поиска, инлайнов и действий. Реализовано мягкое удаление
через :class:`SoftDeleteAdmin` — миксин для моделей с soft delete.
"""

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Category,
    Order,
    OrderItem,
    Product,
    ProductImage,
    Profile,
    Review,
    Sale,
    SiteSettings,
    Specification,
    Tag,
)

# ─── Инлайны ────────────────────────────────


class ProductImageInline(admin.TabularInline):
    """
    Инлайн для изображений товара в админке.

    Отображает изображения товара в табличном виде с миниатюрой (превью).
    Позволяет добавлять новые изображения и помечать их как основные.

    Поля:
        - ``src`` — файл изображения.
        - ``alt`` — альтернативный текст.
        - ``is_preview`` — флаг основного изображения.
        - ``image_thumbnail`` — миниатюра (только для чтения).
    """

    model = ProductImage
    extra = 1
    fields = ("src", "alt", "is_preview", "image_thumbnail")
    readonly_fields = ("image_thumbnail",)

    @admin.display(description="Превью")
    def image_thumbnail(self, obj: ProductImage) -> str:
        """
        Отобразить миниатюру изображения.

        Args:
            obj: Экземпляр :class:`~shopapp.models.ProductImage`.

        Returns:
            HTML-тег ``<img>`` с миниатюрой или «—» если изображения нет.
        """
        if obj.src:
            return format_html(
                '<img src="{}" style="max-height:80px; max-width:120px;" />',
                obj.src.url,
            )
        return "—"


class SpecificationInline(admin.TabularInline):
    """Инлайн для характеристик товара (пары «название — значение»)."""

    model = Specification
    extra = 1


class ReviewInline(admin.TabularInline):
    """
    Инлайн для отзывов в карточке товара (только для чтения).

    Все поля доступны только для просмотра — редактирование отзывов
    возможно в отдельном разделе :class:`ReviewAdmin`.
    """

    model = Review
    extra = 0
    readonly_fields = ("author", "email", "text", "rate", "date")


class OrderItemInline(admin.TabularInline):
    """Инлайн для позиций заказа (товар, цена, количество)."""

    model = OrderItem
    extra = 0


# ─── Миксин мягкого удаления для админки ─────


class SoftDeleteAdmin(admin.ModelAdmin):
    """
    Базовый класс для админки моделей с мягким удалением.

    Переопределяет ``get_queryset`` для отображения всех записей
    (включая мягко удалённые) через ``all_objects``.
    Добавляет действия «Мягкое удаление выбранных» и «Восстановить выбранные».
    """

    def get_queryset(self, request):
        """Вернуть QuerySet, включающий мягко удалённые объекты."""
        return self.model.all_objects.all()

    actions = ["soft_delete_selected", "restore_selected"]

    @admin.action(description="Мягкое удаление выбранных")
    def soft_delete_selected(self, request, queryset) -> None:
        """Выполнить мягкое удаление для всех выбранных объектов."""
        for obj in queryset:
            obj.soft_delete()

    @admin.action(description="Восстановить выбранные")
    def restore_selected(self, request, queryset) -> None:
        """Восстановить все выбранные мягко удалённые объекты."""
        for obj in queryset:
            obj.restore()


# ─── Регистрация моделей ─────────────────────


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """
    Админка профилей пользователей.

    Отображает: пользователя, ФИО, телефон.
    Поиск по ФИО, телефону и имени пользователя.
    """

    list_display = ("user", "full_name", "phone")
    search_fields = ("full_name", "phone", "user__username")


@admin.register(Category)
class CategoryAdmin(SoftDeleteAdmin):
    """
    Админка категорий товаров.

    Поддерживает мягкое удаление. В списке редактируются:
    ``is_active``, ``is_deleted``, ``sort_index``.
    Фильтры: по активности, удалению, родительской категории.
    """

    list_display = ("title", "parent", "is_active", "sort_index", "is_deleted")
    list_editable = ("is_active", "is_deleted", "sort_index")
    list_filter = ("is_active", "is_deleted", "parent")
    search_fields = ("title",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Админка тегов. Отображает ID и название, поиск по названию."""

    list_display = ("id", "name")
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(SoftDeleteAdmin):
    """
    Админка товаров — центральный раздел управления каталогом.

    Особенности:
        - Инлайны: изображения (с миниатюрами), характеристики, отзывы.
        - ``list_editable``: ``limited_edition`` и ``is_deleted`` редактируются в списке.
        - ``filter_horizontal``: удобный виджет выбора тегов.
        - Fieldsets: группировка полей по разделам (основное, описание, параметры, удаление).
    """

    list_display = (
        "title",
        "category",
        "price",
        "count",
        "rating",
        "limited_edition",
        "is_deleted",
    )
    list_editable = ("limited_edition", "is_deleted")
    list_filter = ("category", "free_delivery", "limited_edition", "is_deleted")
    search_fields = ("title", "description")
    inlines = [ProductImageInline, SpecificationInline, ReviewInline]
    filter_horizontal = ("tags",)
    fieldsets = (
        (
            "Основное",
            {
                "fields": ("title", "category", "price", "count", "tags"),
            },
        ),
        (
            "Описание",
            {
                "fields": ("description", "full_description"),
                "classes": ("collapse",),
            },
        ),
        (
            "Параметры",
            {
                "fields": (
                    "sort_index",
                    "free_delivery",
                    "limited_edition",
                    "rating",
                    "purchases_count",
                ),
            },
        ),
        (
            "Мягкое удаление",
            {
                "fields": ("is_deleted", "deleted_at"),
                "classes": ("collapse",),
            },
        ),
    )
    readonly_fields = ("deleted_at",)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Админка отзывов. Фильтр по оценке, поиск по автору и тексту."""

    list_display = ("product", "author", "rate", "date")
    list_filter = ("rate",)
    search_fields = ("author", "text")


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    """Админка скидок. Фильтр по датам начала и окончания."""

    list_display = ("product", "sale_price", "date_from", "date_to")
    list_filter = ("date_from", "date_to")


@admin.register(Order)
class OrderAdmin(SoftDeleteAdmin):
    """
    Админка заказов с мягким удалением.

    Инлайн позиций заказа (:class:`OrderItemInline`).
    Фильтры: статус, способ доставки/оплаты, удаление.
    Поиск по ФИО, email, телефону.
    """

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
    """
    Админка настроек сайта (Singleton).

    Ограничения:
        - Добавление новой записи разрешено только если записей нет (``has_add_permission``).
        - Удаление запрещено (``has_delete_permission``).

    Гарантирует единственный экземпляр настроек в базе.
    """

    list_display = (
        "express_delivery_cost",
        "ordinary_delivery_cost",
        "free_delivery_threshold",
    )

    def has_add_permission(self, request) -> bool:
        """Разрешить добавление только если записи ещё нет (Singleton)."""
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None) -> bool:
        """Запретить удаление настроек сайта."""
        return False
