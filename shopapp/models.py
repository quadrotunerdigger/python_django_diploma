"""
Модели приложения shopapp.

Содержит модели данных интернет-магазина Megano:
профили пользователей, категории, товары, изображения,
характеристики, отзывы, скидки, заказы и настройки сайта.
Реализовано мягкое удаление (soft delete) через абстрактную модель.
"""

from django.contrib.auth.models import User
from django.db import models


class SoftDeleteManager(models.Manager):
    """
    Менеджер, исключающий из выборки мягко удалённые объекты.

    Переопределяет стандартный QuerySet, добавляя фильтр ``is_deleted=False``.
    Используется как ``objects`` в моделях, наследующих :class:`SoftDeleteModel`.
    Для доступа ко всем записям (включая удалённые) используется ``all_objects``.
    """

    def get_queryset(self) -> models.QuerySet:
        """Вернуть QuerySet без мягко удалённых записей."""
        return super().get_queryset().filter(is_deleted=False)


class SoftDeleteModel(models.Model):
    """
    Абстрактная модель с поддержкой мягкого удаления.

    Вместо физического удаления записи из базы данных устанавливает
    флаг ``is_deleted=True`` и сохраняет дату удаления в ``deleted_at``.
    Предоставляет два менеджера:

    - ``objects`` — :class:`SoftDeleteManager`, возвращает только активные записи.
    - ``all_objects`` — стандартный ``Manager``, возвращает все записи.

    Методы :meth:`soft_delete` и :meth:`restore` управляют состоянием удаления.
    """

    is_deleted = models.BooleanField(default=False, verbose_name="удалён")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="дата удаления")  # type: ignore[misc]

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def soft_delete(self) -> None:
        """
        Выполнить мягкое удаление записи.

        Устанавливает ``is_deleted=True`` и фиксирует текущее время в ``deleted_at``.
        """
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self) -> None:
        """
        Восстановить мягко удалённую запись.

        Сбрасывает ``is_deleted=False`` и очищает ``deleted_at``.
        """
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


# ─────────────────────────────────────────────
# Профиль пользователя
# ─────────────────────────────────────────────


class Profile(models.Model):
    """
    Расширенный профиль пользователя.

    Связан с моделью ``User`` отношением один-к-одному.
    Хранит дополнительные данные: ФИО, телефон и аватар.
    Телефон уникален (``unique=True``) для предотвращения дублирования.

    Пример использования::

        profile = request.user.profile
        print(profile.full_name, profile.phone)
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    full_name = models.CharField(max_length=255, blank=True, verbose_name="ФИО")
    phone = models.CharField(  # type: ignore[misc]
        max_length=20, blank=True, unique=True, null=True, verbose_name="телефон"
    )
    avatar = models.ImageField(upload_to="avatars/", blank=True, null=True, verbose_name="аватар")

    class Meta:
        verbose_name = "профиль"
        verbose_name_plural = "профили"

    def __str__(self) -> str:
        """Вернуть ФИО профиля или username пользователя."""
        return self.full_name or self.user.username


# ─────────────────────────────────────────────
# Категории (вложенность до 2 уровней)
# ─────────────────────────────────────────────


class Category(SoftDeleteModel):
    """
    Категория товаров с поддержкой двухуровневой вложенности.

    Родительские категории имеют ``parent=None``, подкатегории ссылаются
    на родителя через внешний ключ ``parent``. Поддерживается мягкое удаление.

    Примеры структуры::

        Электроника (parent=None)
        ├── Смартфоны (parent=Электроника)
        ├── Наушники (parent=Электроника)
        └── Колонки (parent=Электроника)

    Атрибуты:
        title: Название категории.
        image: Иконка категории (загружается в ``media/categories/``).
        parent: Ссылка на родительскую категорию (``None`` для корневых).
        is_active: Флаг активности (неактивные не отображаются на сайте).
        sort_index: Индекс сортировки для управления порядком вывода.
    """

    title = models.CharField(max_length=255, verbose_name="название")
    image = models.ImageField(upload_to="categories/", blank=True, null=True, verbose_name="иконка")
    parent = models.ForeignKey(  # type: ignore[misc]
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

    def __str__(self) -> str:
        """Вернуть название категории."""
        return self.title


# ─────────────────────────────────────────────
# Теги
# ─────────────────────────────────────────────


class Tag(models.Model):
    """
    Тег для фильтрации товаров в каталоге.

    Теги связаны с товарами через ``ManyToManyField``.
    Используются для быстрой фильтрации: Gaming, Office, Budget и т.д.
    """

    name = models.CharField(max_length=100, verbose_name="название")

    class Meta:
        verbose_name = "тег"
        verbose_name_plural = "теги"

    def __str__(self) -> str:
        """Вернуть название тега."""
        return self.name


# ─────────────────────────────────────────────
# Товар
# ─────────────────────────────────────────────


class Product(SoftDeleteModel):
    """
    Товар интернет-магазина.

    Центральная модель приложения. Содержит всю информацию о товаре:
    название, описание, цену, количество на складе, рейтинг и др.
    Поддерживает мягкое удаление через :class:`SoftDeleteModel`.

    Связи:
        - ``category`` → :class:`Category` (FK, может быть ``NULL`` при удалении категории).
        - ``tags`` → :class:`Tag` (M2M, для фильтрации в каталоге).
        - ``images`` → :class:`ProductImage` (обратная связь, изображения товара).
        - ``specifications`` → :class:`Specification` (обратная связь, характеристики).
        - ``reviews`` → :class:`Review` (обратная связь, отзывы покупателей).
        - ``sales`` → :class:`Sale` (обратная связь, скидки).

    Атрибуты:
        title: Название товара.
        description: Краткое описание (отображается в каталоге).
        full_description: Полное описание в HTML (отображается на детальной странице).
        price: Базовая цена товара (скидочная цена — в модели :class:`Sale`).
        count: Количество на складе (0 = нет в наличии).
        free_delivery: Флаг бесплатной доставки.
        limited_edition: Флаг ограниченного тиража (для блока Limited Edition).
        rating: Средний рейтинг (пересчитывается при добавлении отзыва).
        purchases_count: Счётчик покупок (увеличивается при оплате заказа).
    """

    category = models.ForeignKey(  # type: ignore[misc]
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
    limited_edition = models.BooleanField(default=False, verbose_name="ограниченный тираж")
    sort_index = models.PositiveIntegerField(default=0, verbose_name="индекс сортировки")
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0, verbose_name="рейтинг")
    purchases_count = models.PositiveIntegerField(default=0, verbose_name="количество покупок")
    tags = models.ManyToManyField(Tag, blank=True, related_name="products", verbose_name="теги")

    class Meta:
        verbose_name = "товар"
        verbose_name_plural = "товары"
        ordering = ["sort_index", "-purchases_count"]

    def __str__(self) -> str:
        """Вернуть название товара."""
        return self.title


def product_image_upload_to(instance: "ProductImage", filename: str) -> str:
    """
    Определить путь загрузки изображения товара.

    Формирует путь вида::

        media/products/<Категория>/<Название_товара>/preview/<filename>
        media/products/<Категория>/<Название_товара>/images/<filename>

    Названия категории и товара очищаются от спецсимволов,
    пробелы заменяются на подчёркивания.

    Args:
        instance: Экземпляр :class:`ProductImage`.
        filename: Оригинальное имя загружаемого файла.

    Returns:
        Относительный путь для сохранения файла в ``MEDIA_ROOT``.
    """
    import re

    product = instance.product
    product_name = re.sub(r"[^\w\s.-]", "", product.title).strip().replace(" ", "_")
    category_name = "Uncategorized"
    if product.category:
        category_name = re.sub(r"[^\w\s.-]", "", product.category.title).strip().replace(" ", "_")

    subfolder = "preview" if instance.is_preview else "images"
    return f"products/{category_name}/{product_name}/{subfolder}/{filename}"


class ProductImage(models.Model):
    """
    Изображение товара.

    Каждый товар может иметь несколько изображений. Одно из них помечается
    как превью (``is_preview=True``) — оно отображается в каталоге и списках.
    Остальные показываются в галерее на детальной странице товара.

    Путь загрузки определяется функцией :func:`product_image_upload_to`.
    Сортировка: превью-изображения идут первыми, затем по ``pk``.
    """

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images", verbose_name="товар"
    )
    src = models.ImageField(upload_to=product_image_upload_to, verbose_name="изображение")
    alt = models.CharField(max_length=255, blank=True, verbose_name="alt-текст")
    is_preview = models.BooleanField(default=False, verbose_name="основное изображение (preview)")

    class Meta:
        verbose_name = "изображение товара"
        verbose_name_plural = "изображения товаров"
        ordering = ["-is_preview", "pk"]

    def __str__(self) -> str:
        """Вернуть строковое представление с пометкой [preview] для превью."""
        tag = " [preview]" if self.is_preview else ""
        return f"Image for {self.product.title}{tag}"


class Specification(models.Model):
    """
    Характеристика товара (пара «название — значение»).

    Отображается на детальной странице товара во вкладке «Описание».
    Примеры: «Производитель: Apple», «Гарантия: 24 мес.».
    """

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

    def __str__(self) -> str:
        """Вернуть характеристику в формате 'название: значение'."""
        return f"{self.name}: {self.value}"


# ─────────────────────────────────────────────
# Отзывы
# ─────────────────────────────────────────────


class Review(models.Model):
    """
    Отзыв покупателя о товаре.

    Содержит имя автора, email, текст отзыва и оценку (1–5).
    Добавлять отзывы могут только авторизованные пользователи (проверка во view).
    При добавлении отзыва пересчитывается средний рейтинг товара.

    Сортировка по умолчанию: сначала новые отзывы (``-date``).
    """

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

    def __str__(self) -> str:
        """Вернуть строку вида 'Отзыв от <автор> на <товар>'."""
        return f"Отзыв от {self.author} на {self.product.title}"


# ─────────────────────────────────────────────
# Скидки / распродажи
# ─────────────────────────────────────────────


class Sale(models.Model):
    """
    Скидка (распродажа) на товар с ограничением по датам.

    Активная скидка определяется условием:
    ``date_from <= сегодня <= date_to``.
    Если скидка активна, в каталоге и на странице товара
    отображается ``sale_price`` вместо базовой цены.

    Отображается на странице ``/sale/`` с пагинацией.
    """

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

    def __str__(self) -> str:
        """Вернуть строку вида 'Скидка на <товар>'."""
        return f"Скидка на {self.product.title}"


# ─────────────────────────────────────────────
# Заказы
# ─────────────────────────────────────────────


class Order(SoftDeleteModel):
    """
    Заказ покупателя.

    Жизненный цикл заказа::

        created → accepted (подтверждён) → paid (оплачен)
                                         → payment_error (ошибка оплаты)

    Поддерживает мягкое удаление через :class:`SoftDeleteModel`.

    Вложенные классы ``DeliveryType``, ``PaymentType``, ``Status``
    определяют допустимые значения для соответствующих полей
    через ``TextChoices``.

    Связи:
        - ``user`` → ``User`` (покупатель, создавший заказ).
        - ``items`` → :class:`OrderItem` (обратная связь, позиции заказа).

    Атрибуты:
        delivery_type: Способ доставки (обычная / экспресс).
        payment_type: Способ оплаты (онлайн картой / со случайного счёта).
        total_cost: Итоговая стоимость с учётом доставки.
        status: Текущий статус заказа.
        payment_error: Текст ошибки оплаты (``None`` при успешной оплате).
    """

    class DeliveryType(models.TextChoices):
        """Варианты способа доставки."""

        ORDINARY = "ordinary", "Обычная доставка"
        EXPRESS = "express", "Экспресс-доставка"

    class PaymentType(models.TextChoices):
        """Варианты способа оплаты."""

        ONLINE = "online", "Онлайн картой"
        SOMEONE = "someone", "Онлайн со случайного чужого счёта"

    class Status(models.TextChoices):
        """Статусы заказа."""

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
    payment_error = models.CharField(  # type: ignore[misc]
        max_length=255, blank=True, null=True, verbose_name="ошибка оплаты"
    )

    class Meta:
        verbose_name = "заказ"
        verbose_name_plural = "заказы"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        """Вернуть строку вида 'Заказ #<id> от <ФИО>'."""
        return f"Заказ #{self.pk} от {self.full_name}"


class OrderItem(models.Model):
    """
    Позиция (строка) заказа.

    Связывает заказ с конкретным товаром, фиксируя цену на момент покупки
    и количество единиц. Цена сохраняется отдельно от текущей цены товара,
    чтобы изменение цен не влияло на уже оформленные заказы.
    """

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name="заказ"
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="товар")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="цена на момент покупки"
    )
    count = models.PositiveIntegerField(default=1, verbose_name="количество")

    class Meta:
        verbose_name = "позиция заказа"
        verbose_name_plural = "позиции заказа"

    def __str__(self) -> str:
        """Вернуть строку вида '<товар> x<количество>'."""
        return f"{self.product.title} x{self.count}"


# ─────────────────────────────────────────────
# Настройки магазина (singleton)
# ─────────────────────────────────────────────


class SiteSettings(models.Model):
    """
    Глобальные настройки интернет-магазина (паттерн Singleton).

    Гарантируется единственная запись в базе (``pk=1``).
    Метод :meth:`save` принудительно устанавливает ``pk=1``,
    метод :meth:`load` создаёт или возвращает существующую запись.

    Настройки:
        express_delivery_cost: Стоимость экспресс-доставки (по умолчанию 500₽).
        ordinary_delivery_cost: Стоимость обычной доставки (по умолчанию 200₽).
        free_delivery_threshold: Порог бесплатной доставки (по умолчанию 2000₽).

    Пример использования::

        settings = SiteSettings.load()
        if total >= settings.free_delivery_threshold:
            delivery_cost = 0
    """

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

    def save(self, *args, **kwargs) -> None:
        """Сохранить настройки, принудительно устанавливая ``pk=1`` (Singleton)."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls) -> "SiteSettings":
        """
        Загрузить единственный экземпляр настроек.

        Если запись не существует, создаёт её с значениями по умолчанию.

        Returns:
            Экземпляр :class:`SiteSettings`.
        """
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self) -> str:
        """Вернуть строку 'Настройки сайта'."""
        return "Настройки сайта"
