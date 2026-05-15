from django.db import models
from django.contrib.auth.models import User


class SoftDeleteManager(models.Manager):
    """Manager that filters out soft-deleted objects."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """Abstract model with soft delete support."""

    is_deleted = models.BooleanField(default=False, verbose_name="удалён")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="дата удаления")

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self):
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


# ─────────────────────────────────────────────
# Профиль пользователя
# ─────────────────────────────────────────────


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=255, blank=True, verbose_name="ФИО")
    phone = models.CharField(
        max_length=20, blank=True, unique=True, null=True, verbose_name="телефон"
    )
    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True, verbose_name="аватар"
    )

    class Meta:
        verbose_name = "профиль"
        verbose_name_plural = "профили"

    def __str__(self):
        return self.full_name or self.user.username


# ─────────────────────────────────────────────
# Категории (вложенность до 2 уровней)
# ─────────────────────────────────────────────


class Category(SoftDeleteModel):
    title = models.CharField(max_length=255, verbose_name="название")
    image = models.ImageField(
        upload_to="categories/", blank=True, null=True, verbose_name="иконка"
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategories",
        verbose_name="родительская категория",
    )
    is_active = models.BooleanField(default=True, verbose_name="активна")
    sort_index = models.PositiveIntegerField(default=0, verbose_name="индекс сортировки")

    class Meta:
        verbose_name = "категория"
        verbose_name_plural = "категории"
        ordering = ["sort_index", "title"]

    def __str__(self):
        return self.title


# ─────────────────────────────────────────────
# Теги
# ─────────────────────────────────────────────


class Tag(models.Model):
    name = models.CharField(max_length=100, verbose_name="название")

    class Meta:
        verbose_name = "тег"
        verbose_name_plural = "теги"

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────
# Товар
# ─────────────────────────────────────────────


class Product(SoftDeleteModel):
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        related_name="products",
        verbose_name="категория",
    )
    title = models.CharField(max_length=255, verbose_name="название")
    description = models.TextField(blank=True, verbose_name="краткое описание")
    full_description = models.TextField(blank=True, verbose_name="полное описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="цена")
    count = models.PositiveIntegerField(default=0, verbose_name="количество на складе")
    date = models.DateTimeField(auto_now_add=True, verbose_name="дата создания")
    free_delivery = models.BooleanField(default=False, verbose_name="бесплатная доставка")
    limited_edition = models.BooleanField(
        default=False, verbose_name="ограниченный тираж"
    )
    sort_index = models.PositiveIntegerField(default=0, verbose_name="индекс сортировки")
    rating = models.DecimalField(
        max_digits=3, decimal_places=1, default=0, verbose_name="рейтинг"
    )
    purchases_count = models.PositiveIntegerField(
        default=0, verbose_name="количество покупок"
    )
    tags = models.ManyToManyField(
        Tag, blank=True, related_name="products", verbose_name="теги"
    )

    class Meta:
        verbose_name = "товар"
        verbose_name_plural = "товары"
        ordering = ["sort_index", "-purchases_count"]

    def __str__(self):
        return self.title


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images", verbose_name="товар"
    )
    src = models.ImageField(upload_to="products/", verbose_name="изображение")
    alt = models.CharField(max_length=255, blank=True, verbose_name="alt-текст")

    class Meta:
        verbose_name = "изображение товара"
        verbose_name_plural = "изображения товаров"

    def __str__(self):
        return f"Image for {self.product.title}"


class Specification(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="specifications",
        verbose_name="товар",
    )
    name = models.CharField(max_length=255, verbose_name="характеристика")
    value = models.CharField(max_length=255, verbose_name="значение")

    class Meta:
        verbose_name = "характеристика"
        verbose_name_plural = "характеристики"

    def __str__(self):
        return f"{self.name}: {self.value}"


# ─────────────────────────────────────────────
# Отзывы
# ─────────────────────────────────────────────


class Review(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews", verbose_name="товар"
    )
    author = models.CharField(max_length=255, verbose_name="автор")
    email = models.EmailField(verbose_name="email")
    text = models.TextField(verbose_name="текст отзыва")
    rate = models.PositiveSmallIntegerField(default=5, verbose_name="оценка")
    date = models.DateTimeField(auto_now_add=True, verbose_name="дата")

    class Meta:
        verbose_name = "отзыв"
        verbose_name_plural = "отзывы"
        ordering = ["-date"]

    def __str__(self):
        return f"Отзыв от {self.author} на {self.product.title}"


# ─────────────────────────────────────────────
# Скидки / распродажи
# ─────────────────────────────────────────────


class Sale(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="sales", verbose_name="товар"
    )
    sale_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="цена со скидкой"
    )
    date_from = models.DateField(verbose_name="дата начала")
    date_to = models.DateField(verbose_name="дата окончания")

    class Meta:
        verbose_name = "скидка"
        verbose_name_plural = "скидки"

    def __str__(self):
        return f"Скидка на {self.product.title}"


# ─────────────────────────────────────────────
# Заказы
# ─────────────────────────────────────────────


class Order(SoftDeleteModel):
    class DeliveryType(models.TextChoices):
        ORDINARY = "ordinary", "Обычная доставка"
        EXPRESS = "express", "Экспресс-доставка"

    class PaymentType(models.TextChoices):
        ONLINE = "online", "Онлайн картой"
        SOMEONE = "someone", "Онлайн со случайного чужого счёта"

    class Status(models.TextChoices):
        CREATED = "created", "Создан"
        ACCEPTED = "accepted", "Принят"
        PAID = "paid", "Оплачен"
        PAYMENT_ERROR = "payment_error", "Ошибка оплаты"

    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="orders", verbose_name="покупатель"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="дата создания")
    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    email = models.EmailField(verbose_name="email")
    phone = models.CharField(max_length=20, verbose_name="телефон")
    delivery_type = models.CharField(
        max_length=10,
        choices=DeliveryType.choices,
        default=DeliveryType.ORDINARY,
        verbose_name="способ доставки",
    )
    payment_type = models.CharField(
        max_length=10,
        choices=PaymentType.choices,
        default=PaymentType.ONLINE,
        verbose_name="способ оплаты",
    )
    total_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="общая стоимость"
    )
    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.CREATED,
        verbose_name="статус",
    )
    city = models.CharField(max_length=255, blank=True, verbose_name="город")
    address = models.TextField(blank=True, verbose_name="адрес")
    comment = models.TextField(blank=True, verbose_name="комментарий")
    payment_error = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="ошибка оплаты"
    )

    class Meta:
        verbose_name = "заказ"
        verbose_name_plural = "заказы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заказ #{self.pk} от {self.full_name}"


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name="заказ"
    )
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, verbose_name="товар"
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="цена на момент покупки"
    )
    count = models.PositiveIntegerField(default=1, verbose_name="количество")

    class Meta:
        verbose_name = "позиция заказа"
        verbose_name_plural = "позиции заказа"

    def __str__(self):
        return f"{self.product.title} x{self.count}"


# ─────────────────────────────────────────────
# Настройки магазина (singleton)
# ─────────────────────────────────────────────


class SiteSettings(models.Model):
    express_delivery_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=500,
        verbose_name="стоимость экспресс-доставки",
    )
    ordinary_delivery_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=200,
        verbose_name="стоимость обычной доставки",
    )
    free_delivery_threshold = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=2000,
        verbose_name="порог бесплатной доставки",
    )

    class Meta:
        verbose_name = "настройки сайта"
        verbose_name_plural = "настройки сайта"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Настройки сайта"
