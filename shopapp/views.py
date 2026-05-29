"""
API-представления (views) приложения shopapp.

Содержит все эндпоинты REST API интернет-магазина Megano:
аутентификация, каталог, товары, корзина (сессионная),
заказы, фиктивная оплата, профиль пользователя.

Все представления наследуют ``django.views.View`` и возвращают ``JsonResponse``.
CSRF-защита отключена через ``@csrf_exempt`` для API-эндпоинтов,
принимающих POST/DELETE-запросы.
"""

import json
import math
import random
from typing import Any, Optional

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Count, Q, QuerySet
from django.http import HttpRequest, JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Category,
    Order,
    OrderItem,
    Product,
    Profile,
    Review,
    Sale,
    SiteSettings,
    Tag,
)

# ═══════════════════════════════════════════════
# Вспомогательные функции
# ═══════════════════════════════════════════════


def _get_active_sale_price(product: Product) -> Optional[float]:
    """
    Получить актуальную скидочную цену товара.

    Проверяет наличие активной скидки (``date_from <= сегодня <= date_to``).

    Args:
        product: Экземпляр товара.

    Returns:
        Цена со скидкой (``float``) или ``None``, если активных скидок нет.
    """
    from django.utils import timezone

    today = timezone.now().date()
    sale = product.sales.filter(date_from__lte=today, date_to__gte=today).first()
    if sale:
        return float(sale.sale_price)
    return None


def _product_short(product: Product) -> dict[str, Any]:
    """
    Сериализовать товар в краткий формат.

    Используется в каталоге, популярных товарах, ограниченном тираже,
    корзине и списках заказов. Включает основные поля товара,
    изображения, теги, количество отзывов и рейтинг.

    Если у товара есть активная скидка, подставляет ``sale_price``
    вместо базовой цены.

    Args:
        product: Экземпляр товара.

    Returns:
        Словарь с данными товара для JSON-ответа.
    """
    images = list(product.images.all().order_by("-is_preview", "pk").values("src", "alt"))
    for img in images:
        if img["src"] and not img["src"].startswith("/"):
            img["src"] = "/media/" + img["src"]
    tags = list(product.tags.all().values("id", "name"))
    reviews_count = product.reviews.count()

    price = float(product.price)
    sale_price = _get_active_sale_price(product)

    return {
        "id": product.pk,
        "category": product.category_id,
        "price": sale_price if sale_price else price,
        "count": product.count,
        "date": product.date.isoformat() if product.date else "",
        "title": product.title,
        "description": product.description,
        "freeDelivery": product.free_delivery,
        "images": images if images else [{"src": "", "alt": ""}],
        "tags": tags,
        "reviews": reviews_count,
        "rating": float(product.rating),
    }


def _product_full(product: Product) -> dict[str, Any]:
    """
    Сериализовать товар в полный формат для детальной страницы.

    Расширяет :func:`_product_short`, добавляя полное описание,
    список характеристик и все отзывы с форматированными датами.

    Args:
        product: Экземпляр товара.

    Returns:
        Словарь с полными данными товара для JSON-ответа.
    """
    data = _product_short(product)
    data["fullDescription"] = product.full_description
    data["specifications"] = list(product.specifications.all().values("name", "value"))
    data["reviews"] = list(product.reviews.all().values("author", "email", "text", "rate", "date"))
    for r in data["reviews"]:
        if r["date"]:
            r["date"] = r["date"].strftime("%Y-%m-%d %H:%M")  # type: ignore[typeddict-item]
    return data


def _category_data(category: Category) -> dict[str, Any]:
    """
    Сериализовать категорию с подкатегориями.

    Возвращает словарь с ``id``, ``title``, ``image`` и списком
    подкатегорий (``subcategories``). Иконки определяются через
    :func:`_category_icon`.

    Args:
        category: Экземпляр родительской категории.

    Returns:
        Словарь с данными категории и её подкатегорий.
    """
    image = _category_icon(category)
    subcats = []
    for sub in Category.objects.filter(parent=category, is_active=True):
        subcats.append(
            {
                "id": sub.pk,
                "title": sub.title,
                "image": _category_icon(sub),
            }
        )
    return {
        "id": category.pk,
        "title": category.title,
        "image": image,
        "subcategories": subcats,
    }


# Соответствие названий категорий номерам SVG-иконок (1.svg – 12.svg)
_CATEGORY_ICON_MAP: dict[str, int] = {
    # Родительские категории
    "Бытовая техника": 3,
    "Электроника": 5,
    "Компьютеры и комплектующие": 1,
    # Бытовая техника — подкатегории
    "Стиральные машины": 3,
    "Пылесосы": 4,
    "Холодильники": 4,
    "Электрические плиты и печи": 7,
    "Печи СВЧ": 9,
    "Миксеры и блендеры": 12,
    "Настольные лампы": 11,
    "Чайники": 10,
    # Электроника — подкатегории
    "Смартфоны": 8,
    "Наушники": 2,
    "Колонки": 5,
    "Фотоаппараты": 6,
    # Компьютеры — подкатегории
    "Видеокарты": 4,
    "Процессоры": 4,
    "Мониторы": 1,
    "Ноутбуки и планшеты": 4,
}


def _category_icon(category: Category) -> dict[str, str]:
    """
    Получить иконку категории.

    Приоритет: загруженное изображение ``category.image``.
    Если его нет, используется статическая SVG-иконка из
    ``/static/frontend/assets/img/icons/departments/{N}.svg``
    на основе маппинга :data:`_CATEGORY_ICON_MAP`.

    Args:
        category: Экземпляр категории.

    Returns:
        Словарь ``{"src": "<url>", "alt": "<название>"}``
    """
    if category.image:
        return {"src": category.image.url, "alt": category.title}
    icon_num = _CATEGORY_ICON_MAP.get(category.title)
    if icon_num:
        return {
            "src": f"/static/frontend/assets/img/icons/departments/{icon_num}.svg",
            "alt": category.title,
        }
    return {"src": "", "alt": category.title}


def _parse_json_body(request: HttpRequest) -> dict[str, Any]:
    """
    Извлечь JSON-данные из тела HTTP-запроса.

    Args:
        request: HTTP-запрос с JSON-телом.

    Returns:
        Словарь с распарсенными данными или пустой словарь при ошибке.
    """
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return {}


def _get_basket(request: HttpRequest) -> dict[str, int]:
    """
    Получить корзину из сессии.

    Args:
        request: HTTP-запрос.

    Returns:
        Словарь ``{product_id_str: count}``.
    """
    return request.session.get("basket", {})


def _set_basket(request: HttpRequest, basket: dict[str, int]) -> None:
    """
    Сохранить корзину в сессию.

    Args:
        request: HTTP-запрос.
        basket: Словарь ``{product_id_str: count}``.
    """
    request.session["basket"] = basket
    request.session.modified = True


def _basket_response(request: HttpRequest) -> list[dict[str, Any]]:
    """
    Сформировать ответ с содержимым корзины.

    Для каждого товара в сессионной корзине создаёт краткую
    сериализацию через :func:`_product_short` с добавлением
    ``count`` (количество) и актуальной ``price``.

    Args:
        request: HTTP-запрос.

    Returns:
        Список словарей — товары в корзине с количествами.
    """
    basket = _get_basket(request)
    result = []
    for pid_str, count in basket.items():
        try:
            product = Product.objects.get(pk=int(pid_str))
        except Product.DoesNotExist:
            continue
        item = _product_short(product)
        item["count"] = count
        item["price"] = float(product.price)
        result.append(item)
    return result


# ═══════════════════════════════════════════════
# Аутентификация
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class SignInView(View):
    """
    Авторизация пользователя.

    **POST** ``/api/sign-in``

    Тело запроса (JSON)::

        {"username": "buyer1", "password": "123456"}

    Ответы:
        - ``200 {}`` — успешная авторизация.
        - ``500 {"error": "Invalid credentials"}`` — неверные учётные данные.
    """

    def post(self, request: HttpRequest) -> JsonResponse:
        """Авторизовать пользователя по логину и паролю."""
        data = _parse_json_body(request)
        username = data.get("username", "")
        password = data.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return JsonResponse({}, status=200)
        return JsonResponse({"error": "Invalid credentials"}, status=500)


@method_decorator(csrf_exempt, name="dispatch")
class SignUpView(View):
    """
    Регистрация нового пользователя.

    **POST** ``/api/sign-up``

    Тело запроса (JSON)::

        {"name": "Иван Иванов", "username": "ivan", "password": "secret"}

    Создаёт ``User`` и связанный :class:`~shopapp.models.Profile`.
    После регистрации пользователь автоматически авторизуется.

    Ответы:
        - ``200 {}`` — успешная регистрация.
        - ``500 {"error": "User already exists"}`` — имя пользователя занято.
    """

    def post(self, request: HttpRequest) -> JsonResponse:
        """Зарегистрировать нового пользователя."""
        data = _parse_json_body(request)
        name = data.get("name", "")
        username = data.get("username", "")
        password = data.get("password", "")
        if User.objects.filter(username=username).exists():
            return JsonResponse({"error": "User already exists"}, status=500)
        user = User.objects.create_user(username=username, password=password, first_name=name)
        Profile.objects.create(user=user, full_name=name)
        login(request, user)
        return JsonResponse({}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class SignOutView(View):
    """
    Выход пользователя из системы.

    **POST** ``/api/sign-out``

    Завершает текущую сессию. Всегда возвращает ``200 {}``.
    """

    def post(self, request: HttpRequest) -> JsonResponse:
        """Выполнить logout текущего пользователя."""
        logout(request)
        return JsonResponse({}, status=200)


# ═══════════════════════════════════════════════
# Категории
# ═══════════════════════════════════════════════


class CategoryListView(View):
    """
    Список корневых категорий с подкатегориями.

    **GET** ``/api/categories``

    Возвращает JSON-массив категорий верхнего уровня (``parent=None``),
    каждая с вложенным списком подкатегорий. Только активные категории
    (``is_active=True``, не мягко удалённые).
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Вернуть список корневых категорий с подкатегориями."""
        categories = Category.objects.filter(parent__isnull=True, is_active=True)
        result = [_category_data(cat) for cat in categories]
        return JsonResponse(result, safe=False)


# ═══════════════════════════════════════════════
# Каталог (фильтрация, сортировка, пагинация)
# ═══════════════════════════════════════════════


class CatalogView(View):
    """
    Каталог товаров с фильтрами, сортировкой и пагинацией.

    **GET** ``/api/catalog``

    Параметры запроса (query string):
        - ``filter[name]`` / ``filter`` — поиск по названию товара и категории.
        - ``filter[minPrice]``, ``filter[maxPrice]`` — диапазон цен.
        - ``filter[freeDelivery]`` — ``"true"`` для бесплатной доставки.
        - ``filter[available]`` — ``"true"`` для товаров в наличии.
        - ``category`` — ID категории (включая подкатегории).
        - ``tags[]`` — список ID тегов.
        - ``sort`` — поле сортировки: ``rating``, ``price``, ``reviews``, ``date``.
        - ``sortType`` — направление: ``dec`` (по убыванию) / ``inc`` (по возрастанию).
        - ``currentPage`` — номер страницы (по умолчанию 1).
        - ``limit`` — количество товаров на странице (по умолчанию 20).

    Особенности:
        - Поиск по кириллице: SQLite не поддерживает ``icontains`` для кириллицы,
          поэтому используются варианты регистра (capitalize/lower/upper).
        - ``maxPrice=50000`` (дефолт фронтенда) игнорируется.
        - Поиск выполняется по названию товара, категории и родительской категории.

    Ответ::

        {
            "items": [...],
            "currentPage": 1,
            "lastPage": 3
        }
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Вернуть список товаров с учётом фильтров, сортировки и пагинации."""
        # Фильтры
        name = request.GET.get("filter[name]", "")
        if not name:
            name = request.GET.get("filter", "")
        min_price = request.GET.get("filter[minPrice]")
        max_price = request.GET.get("filter[maxPrice]")
        free_delivery = request.GET.get("filter[freeDelivery]", "false")
        available = request.GET.get("filter[available]", "false")
        category_id = request.GET.get("category")
        tags_list = request.GET.getlist("tags[]")

        # Сортировка
        sort_field = request.GET.get("sort", "date")
        sort_type = request.GET.get("sortType", "dec")

        # Пагинация
        current_page = int(request.GET.get("currentPage", 1))
        limit = int(request.GET.get("limit", 20))

        qs: QuerySet[Product] = Product.objects.all()

        # Фильтрация по названию (с обходом ограничений SQLite для кириллицы)
        if name:
            name_variants = [name, name.capitalize(), name.lower(), name.upper()]
            q = Q()
            for variant in name_variants:
                q |= Q(title__contains=variant)
                q |= Q(category__title__contains=variant)
                q |= Q(category__parent__title__contains=variant)
            q |= Q(title__icontains=name)
            q |= Q(category__title__icontains=name)
            q |= Q(category__parent__title__icontains=name)
            qs = qs.filter(q).distinct()
        if min_price and float(min_price) > 0:
            qs = qs.filter(price__gte=float(min_price))
        if max_price and float(max_price) not in (50000, 50000.0):
            qs = qs.filter(price__lte=float(max_price))
        if free_delivery == "true":
            qs = qs.filter(free_delivery=True)
        if available == "true":
            qs = qs.filter(count__gt=0)
        if category_id:
            cat_ids = [int(category_id)]
            sub_cats = Category.objects.filter(parent_id=int(category_id))
            cat_ids.extend(sub_cats.values_list("id", flat=True))
            qs = qs.filter(category_id__in=cat_ids)
        if tags_list:
            qs = qs.filter(tags__id__in=tags_list).distinct()

        # Сортировка
        sort_map = {
            "rating": "rating",
            "price": "price",
            "reviews": "reviews_count",
            "date": "date",
        }
        if sort_field == "reviews":
            qs = qs.annotate(reviews_count=Count("reviews"))

        order_field = sort_map.get(sort_field, "date")
        if sort_type == "dec":
            order_field = "-" + order_field
        qs = qs.order_by(order_field)

        # Пагинация
        total = qs.count()
        last_page = max(1, math.ceil(total / limit))
        offset = (current_page - 1) * limit
        products = qs[offset : offset + limit]

        items = [_product_short(p) for p in products]
        return JsonResponse(
            {
                "items": items,
                "currentPage": current_page,
                "lastPage": last_page,
            }
        )


# ═══════════════════════════════════════════════
# Популярные товары (топ-8)
# ═══════════════════════════════════════════════


class PopularProductsView(View):
    """
    Список популярных товаров для главной страницы.

    **GET** ``/api/products/popular``

    Возвращает до 8 товаров, отсортированных по ``sort_index``
    и количеству покупок (``purchases_count``) по убыванию.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Вернуть топ-8 популярных товаров."""
        products = Product.objects.order_by("sort_index", "-purchases_count")[:8]
        result = [_product_short(p) for p in products]
        return JsonResponse(result, safe=False)


# ═══════════════════════════════════════════════
# Товары ограниченного тиража (до 16)
# ═══════════════════════════════════════════════


class LimitedProductsView(View):
    """
    Список товаров ограниченного тиража для главной страницы.

    **GET** ``/api/products/limited``

    Возвращает до 16 товаров с ``limited_edition=True``.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Вернуть до 16 товаров ограниченного тиража."""
        products = Product.objects.filter(limited_edition=True)[:16]
        result = [_product_short(p) for p in products]
        return JsonResponse(result, safe=False)


# ═══════════════════════════════════════════════
# Скидки (с пагинацией)
# ═══════════════════════════════════════════════


class SalesView(View):
    """
    Список скидок (распродаж) с пагинацией.

    **GET** ``/api/sales``

    Параметры:
        - ``currentPage`` — номер страницы (по умолчанию 1).

    Возвращает товары со скидками: оригинальную цену, скидочную цену,
    даты действия и изображения.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Вернуть список скидок с пагинацией."""
        current_page = int(request.GET.get("currentPage", 1))
        limit = 20

        sales = Sale.objects.select_related("product").all()
        total = sales.count()
        last_page = max(1, math.ceil(total / limit))
        offset = (current_page - 1) * limit
        page_sales = sales[offset : offset + limit]

        items = []
        for sale in page_sales:
            product = sale.product
            images = list(product.images.all().values("src", "alt"))
            for img in images:
                if img["src"] and not img["src"].startswith("/"):
                    img["src"] = "/media/" + img["src"]
            items.append(
                {
                    "id": product.pk,
                    "price": float(product.price),
                    "salePrice": float(sale.sale_price),
                    "dateFrom": sale.date_from.strftime("%m-%d") if sale.date_from else "",
                    "dateTo": sale.date_to.strftime("%m-%d") if sale.date_to else "",
                    "title": product.title,
                    "images": images if images else [{"src": "", "alt": ""}],
                }
            )
        return JsonResponse(
            {
                "items": items,
                "currentPage": current_page,
                "lastPage": last_page,
            }
        )


# ═══════════════════════════════════════════════
# Баннеры (3 случайных товара для главной)
# ═══════════════════════════════════════════════


class BannersView(View):
    """
    Баннеры для главной страницы.

    **GET** ``/api/banners``

    Возвращает 3 случайных товара, которые есть в наличии.
    Используются в блоке-слайдере на главной странице.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Вернуть 3 случайных товара для баннеров."""
        products = list(Product.objects.filter(count__gt=0).select_related("category")[:50])
        if len(products) > 3:
            products = random.sample(products, 3)
        result = [_product_short(p) for p in products]
        for i, p in enumerate(products):
            result[i]["category"] = p.category_id
        return JsonResponse(result, safe=False)


# ═══════════════════════════════════════════════
# Детальная страница товара
# ═══════════════════════════════════════════════


class ProductDetailView(View):
    """
    Детальная информация о товаре.

    **GET** ``/api/product/<pk>``

    Возвращает полную сериализацию товара: описание, характеристики,
    отзывы, изображения.

    Ответы:
        - ``200`` — данные товара.
        - ``404 {"error": "Not found"}`` — товар не найден.
    """

    def get(self, request: HttpRequest, pk: int) -> JsonResponse:
        """Вернуть полную информацию о товаре по его ID."""
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)
        return JsonResponse(_product_full(product))


# ═══════════════════════════════════════════════
# Отзывы на товар
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class ProductReviewView(View):
    """
    Добавление отзыва к товару.

    **POST** ``/api/product/<pk>/review`` (или ``/reviews``)

    Тело запроса (JSON)::

        {"author": "Иван", "email": "ivan@test.ru", "text": "Отличный товар!", "rate": 5}

    Только для авторизованных пользователей (иначе ``403``).
    Валидация: обязательны ``author``, ``text`` и корректный ``email``.
    После добавления пересчитывается средний рейтинг товара.

    Ответы:
        - ``200`` — массив всех отзывов товара (включая новый).
        - ``400`` — ошибка валидации.
        - ``403`` — пользователь не авторизован.
        - ``404`` — товар не найден.
    """

    def post(self, request: HttpRequest, pk: int) -> JsonResponse:
        """Добавить отзыв к товару и пересчитать средний рейтинг."""
        if not request.user.is_authenticated:
            return JsonResponse(
                {"error": "Необходимо авторизоваться для добавления отзыва"},
                status=403,
            )

        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        data = _parse_json_body(request)

        author: str = data.get("author", "").strip()
        email: str = data.get("email", "").strip()
        text: str = data.get("text", "").strip()
        rate = data.get("rate", 5)

        # Валидация обязательных полей
        if not author:
            return JsonResponse({"error": "Укажите имя"}, status=400)
        if not text:
            return JsonResponse({"error": "Напишите текст отзыва"}, status=400)

        # Валидация email
        import re

        if not email or not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
            return JsonResponse({"error": "Введите корректный email-адрес"}, status=400)

        try:
            rate = int(rate)
            if rate < 1 or rate > 5:
                rate = 5
        except (ValueError, TypeError):
            rate = 5

        Review.objects.create(
            product=product,
            author=author,
            email=email,
            text=text,
            rate=rate,
        )

        # Пересчёт среднего рейтинга товара
        reviews = product.reviews.all()
        if reviews.exists():
            avg = sum(r.rate for r in reviews) / reviews.count()
            product.rating = round(avg, 1)
            product.save(update_fields=["rating"])

        all_reviews = list(reviews.values("author", "email", "text", "rate", "date"))
        for r in all_reviews:
            if r["date"]:
                r["date"] = r["date"].strftime("%Y-%m-%d %H:%M")  # type: ignore[typeddict-item]
        return JsonResponse(all_reviews, safe=False)


# ═══════════════════════════════════════════════
# Теги
# ═══════════════════════════════════════════════


class TagsView(View):
    """
    Список тегов.

    **GET** ``/api/tags``

    Параметры:
        - ``category`` — ID категории для фильтрации тегов.

    Если ``category`` указана, возвращает только теги, привязанные
    к товарам этой категории. Иначе — все теги.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Вернуть список тегов, опционально отфильтрованных по категории."""
        category_id = request.GET.get("category")
        if category_id:
            tags = Tag.objects.filter(products__category_id=int(category_id)).distinct()
        else:
            tags = Tag.objects.all()
        result = list(tags.values("id", "name"))
        return JsonResponse(result, safe=False)


# ═══════════════════════════════════════════════
# Корзина (сессионная)
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class BasketView(View):
    """
    Корзина покупателя (хранится в сессии).

    **GET** ``/api/basket`` — получить содержимое корзины.
    **POST** ``/api/basket`` — добавить товар в корзину.
    **DELETE** ``/api/basket`` — уменьшить количество / удалить товар.

    Тело запроса для POST/DELETE (JSON)::

        {"id": 7, "count": 1}

    Корзина привязана к сессии, а не к пользователю,
    поэтому работает и для неавторизованных посетителей.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Вернуть текущее содержимое корзины."""
        return JsonResponse(_basket_response(request), safe=False)

    def post(self, request: HttpRequest) -> JsonResponse:
        """Добавить товар в корзину (увеличить количество на ``count``)."""
        data = _parse_json_body(request)
        product_id = str(data.get("id", ""))
        count = int(data.get("count", 1))
        basket = _get_basket(request)
        basket[product_id] = basket.get(product_id, 0) + count
        _set_basket(request, basket)
        return JsonResponse(_basket_response(request), safe=False)

    def delete(self, request: HttpRequest) -> JsonResponse:
        """Уменьшить количество товара в корзине (или удалить при count ≤ 0)."""
        data = _parse_json_body(request)
        product_id = str(data.get("id", ""))
        count = int(data.get("count", 1))
        basket = _get_basket(request)
        if product_id in basket:
            basket[product_id] -= count
            if basket[product_id] <= 0:
                del basket[product_id]
        _set_basket(request, basket)
        return JsonResponse(_basket_response(request), safe=False)


# ═══════════════════════════════════════════════
# Заказы
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class OrdersView(View):
    """
    История заказов и создание нового заказа.

    **GET** ``/api/orders`` — список заказов текущего пользователя.
    **POST** ``/api/orders`` — создать новый заказ из корзины.

    При создании заказа:
    1. Товары переносятся из сессионной корзины в позиции заказа.
    2. Фиксируется текущая цена каждого товара.
    3. Корзина очищается.
    4. Заказ создаётся со статусом ``created``.

    Ответы POST:
        - ``200 {"orderId": <id>}`` — заказ создан.
        - ``400`` — корзина пуста.
        - ``403`` — пользователь не авторизован.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Вернуть список заказов текущего пользователя."""
        if not request.user.is_authenticated:
            return JsonResponse([], safe=False)
        orders = Order.objects.filter(user=request.user)
        result = []
        for order in orders:
            result.append(
                {
                    "id": order.pk,
                    "createdAt": order.created_at.strftime("%Y-%m-%d %H:%M"),
                    "fullName": order.full_name,
                    "email": order.email,
                    "phone": order.phone,
                    "deliveryType": order.delivery_type,
                    "paymentType": order.payment_type,
                    "totalCost": float(order.total_cost),
                    "status": order.status,
                    "city": order.city,
                    "address": order.address,
                    "products": [],
                }
            )
        return JsonResponse(result, safe=False)

    def post(self, request: HttpRequest) -> JsonResponse:
        """Создать новый заказ из товаров в корзине."""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Auth required"}, status=403)

        basket_items = _basket_response(request)
        if not basket_items:
            return JsonResponse({"error": "Basket is empty"}, status=400)

        profile = getattr(request.user, "profile", None)
        order = Order.objects.create(
            user=request.user,
            full_name=profile.full_name if profile else request.user.username,
            email=request.user.email or "",
            phone=profile.phone if profile and profile.phone else "",
        )
        total = 0
        for item in basket_items:
            product = Product.objects.get(pk=item["id"])
            count = item["count"]
            OrderItem.objects.create(
                order=order,
                product=product,
                price=product.price,
                count=count,
            )
            total += float(product.price) * count

        order.total_cost = total
        order.save(update_fields=["total_cost"])

        _set_basket(request, {})

        return JsonResponse({"orderId": order.pk})


@method_decorator(csrf_exempt, name="dispatch")
class OrderDetailView(View):
    """
    Детали заказа и подтверждение заказа.

    **GET** ``/api/order/<pk>`` — получить детали заказа с позициями.
    **POST** ``/api/order/<pk>`` — подтвердить заказ (шаг 4 оформления).

    При подтверждении (POST):
    1. Обновляются данные доставки/оплаты из тела запроса.
    2. Пересчитывается итоговая стоимость с учётом доставки.
    3. Статус меняется на ``accepted``.

    Стоимость доставки определяется по настройкам :class:`~shopapp.models.SiteSettings`:
        - Экспресс → ``express_delivery_cost``.
        - Обычная → ``ordinary_delivery_cost`` (или 0, если сумма ≥ ``free_delivery_threshold``).

    Ответы:
        - ``200 {"orderId": <id>}`` — заказ подтверждён.
        - ``404`` — заказ не найден.
    """

    def get(self, request: HttpRequest, pk: int) -> JsonResponse:
        """Вернуть детали заказа с позициями товаров."""
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        products = []
        for item in order.items.select_related("product").all():
            p = _product_short(item.product)
            p["count"] = item.count
            p["price"] = float(item.price)
            products.append(p)

        return JsonResponse(
            {
                "id": order.pk,
                "createdAt": order.created_at.strftime("%Y-%m-%d %H:%M"),
                "fullName": order.full_name,
                "email": order.email,
                "phone": order.phone,
                "deliveryType": order.delivery_type,
                "paymentType": order.payment_type,
                "totalCost": float(order.total_cost),
                "status": order.status,
                "city": order.city,
                "address": order.address,
                "products": products,
                "paymentError": order.payment_error,
            }
        )

    def post(self, request: HttpRequest, pk: int) -> JsonResponse:
        """Подтвердить заказ: обновить данные доставки/оплаты и пересчитать итого."""
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        data = _parse_json_body(request)

        order.full_name = data.get("fullName", order.full_name)
        order.email = data.get("email", order.email)
        order.phone = data.get("phone", order.phone)
        order.delivery_type = data.get("deliveryType", order.delivery_type)
        order.payment_type = data.get("paymentType", order.payment_type)
        order.city = data.get("city", order.city)
        order.address = data.get("address", order.address)
        order.comment = data.get("comment", order.comment)
        order.status = Order.Status.ACCEPTED

        # Пересчёт итоговой стоимости с учётом доставки
        settings = SiteSettings.load()
        products_total = sum(float(item.price) * item.count for item in order.items.all())

        if order.delivery_type == Order.DeliveryType.EXPRESS:
            delivery_cost = float(settings.express_delivery_cost)
        else:
            if products_total < float(settings.free_delivery_threshold):
                delivery_cost = float(settings.ordinary_delivery_cost)
            else:
                delivery_cost = 0

        order.total_cost = products_total + delivery_cost
        order.save()
        return JsonResponse({"orderId": order.pk})


# ═══════════════════════════════════════════════
# Оплата (фиктивный платёжный сервис)
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class PaymentView(View):
    """
    Фиктивная оплата заказа.

    **POST** ``/api/payment/<pk>``

    Тело запроса (JSON)::

        {"number": "12345678", "name": "Иванов", "month": "12", "year": "25", "code": "123"}

    Логика оплаты (по ТЗ):
        1. Номер должен содержать ровно 8 цифр → иначе ошибка.
        2. Номер должен быть чётным → иначе ошибка.
        3. Чётный, не заканчивается на 0 → оплата успешна (``status=paid``).
        4. Чётный, заканчивается на 0 → случайная ошибка (``status=payment_error``).

    При успешной оплате увеличивается ``purchases_count`` для каждого товара.
    Все ошибки возвращаются со статусом HTTP 200 и полем ``error`` в теле,
    чтобы фронтенд мог обработать их в ``.then()``.

    Ответы (все HTTP 200):
        - ``{}`` — оплата прошла успешно.
        - ``{"error": "<текст>"}`` — ошибка оплаты.
    """

    def post(self, request: HttpRequest, pk: int) -> JsonResponse:
        """Обработать оплату заказа по фиктивной логике."""
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        data = _parse_json_body(request)
        number: str = data.get("number", "").replace(" ", "")

        # Валидация: ровно 8 цифр
        if not number.isdigit() or len(number) != 8:
            return JsonResponse(
                {"error": "Номер должен содержать ровно 8 цифр"},
                status=200,
            )

        card_number = int(number)

        # Валидация: номер должен быть чётным
        if card_number % 2 != 0:
            return JsonResponse(
                {"error": "Номер должен быть чётным числом"},
                status=200,
            )

        # Чётный, заканчивается на 0 → случайная ошибка
        if card_number % 10 == 0:
            errors = [
                "Недостаточно средств",
                "Банк отклонил операцию",
                "Превышен лимит",
                "Ошибка обработки платежа",
                "Карта заблокирована",
                "Превышено количество попыток",
            ]
            order.status = Order.Status.PAYMENT_ERROR
            order.payment_error = random.choice(errors)
            order.save(update_fields=["status", "payment_error"])
            return JsonResponse(
                {"error": order.payment_error, "orderId": order.pk},
                status=200,
            )
        # Чётный, не заканчивается на 0 → успешная оплата
        else:
            order.status = Order.Status.PAID
            order.payment_error = None
            order.save(update_fields=["status", "payment_error"])

            # Увеличить счётчик покупок для товаров заказа
            for item in order.items.select_related("product").all():
                item.product.purchases_count += item.count
                item.product.save(update_fields=["purchases_count"])

            return JsonResponse({}, status=200)


# ═══════════════════════════════════════════════
# Профиль пользователя
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class ProfileView(View):
    """
    Профиль текущего пользователя.

    **GET** ``/api/profile`` — получить данные профиля.
    **POST** ``/api/profile`` — обновить данные профиля.

    При обновлении проверяется уникальность телефона и email.

    Ответы:
        - ``200`` — данные профиля.
        - ``400`` — телефон или email уже используется другим пользователем.
        - ``403`` — пользователь не авторизован.
    """

    def get(self, request: HttpRequest) -> JsonResponse:
        """Вернуть данные профиля текущего пользователя."""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Auth required"}, status=403)
        profile, _ = Profile.objects.get_or_create(user=request.user)
        avatar = None
        if profile.avatar:
            avatar = {"src": profile.avatar.url, "alt": profile.full_name}
        return JsonResponse(
            {
                "fullName": profile.full_name,
                "email": request.user.email,
                "phone": profile.phone or "",
                "avatar": avatar,
            }
        )

    def post(self, request: HttpRequest) -> JsonResponse:
        """Обновить ФИО, телефон и email текущего пользователя."""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Auth required"}, status=403)

        data = _parse_json_body(request)
        profile, _ = Profile.objects.get_or_create(user=request.user)

        profile.full_name = data.get("fullName", profile.full_name)
        phone = data.get("phone", profile.phone)
        email = data.get("email", request.user.email)

        # Проверка уникальности телефона и email
        if phone and Profile.objects.filter(phone=phone).exclude(pk=profile.pk).exists():
            return JsonResponse({"error": "Phone already in use"}, status=400)
        if email and User.objects.filter(email=email).exclude(pk=request.user.pk).exists():
            return JsonResponse({"error": "Email already in use"}, status=400)

        profile.phone = phone
        profile.save()

        request.user.email = email
        request.user.save(update_fields=["email"])

        avatar = None
        if profile.avatar:
            avatar = {"src": profile.avatar.url, "alt": profile.full_name}
        return JsonResponse(
            {
                "fullName": profile.full_name,
                "email": request.user.email,
                "phone": profile.phone or "",
                "avatar": avatar,
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class ProfilePasswordView(View):
    """
    Смена пароля пользователя.

    **POST** ``/api/profile/password``

    Тело запроса (JSON)::

        {"currentPassword": "старый", "newPassword": "новый"}

    После смены пароля пользователь автоматически перелогинивается,
    чтобы сессия не инвалидировалась.

    Ответы:
        - ``200 {}`` — пароль успешно изменён.
        - ``400`` — неверный текущий пароль.
        - ``403`` — пользователь не авторизован.
    """

    def post(self, request: HttpRequest) -> JsonResponse:
        """Сменить пароль текущего пользователя."""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Auth required"}, status=403)

        data = _parse_json_body(request)
        current_password: str = data.get("currentPassword", "")
        new_password: str = data.get("newPassword", "")

        if not request.user.check_password(current_password):
            return JsonResponse({"error": "Wrong current password"}, status=400)

        request.user.set_password(new_password)
        request.user.save()
        login(request, request.user)
        return JsonResponse({}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class AvatarView(View):
    """
    Загрузка аватара пользователя.

    **POST** ``/api/profile/avatar``

    Принимает файл через ``multipart/form-data`` в поле ``avatar``.
    Ограничение размера: не более 2 МБ.

    Ответы:
        - ``200 {"src": "<url>", "alt": "<ФИО>"}`` — аватар загружен.
        - ``400`` — файл не передан или превышает 2 МБ.
        - ``403`` — пользователь не авторизован.
    """

    def post(self, request: HttpRequest) -> JsonResponse:
        """Загрузить новый аватар для текущего пользователя."""
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Auth required"}, status=403)

        avatar_file = request.FILES.get("avatar")
        if not avatar_file:
            return JsonResponse({"error": "No file"}, status=400)

        if avatar_file.size > 2 * 1024 * 1024:
            return JsonResponse({"error": "File too large (max 2 MB)"}, status=400)

        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.avatar = avatar_file
        profile.save(update_fields=["avatar"])
        return JsonResponse({"src": profile.avatar.url, "alt": profile.full_name})
