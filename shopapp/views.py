import json
import math
import random

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

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
    Tag,
)


# ═══════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════


def _product_short(product):
    """Serialize product to short format (for catalog, popular, limited, basket)."""
    images = list(product.images.all().values("src", "alt"))
    for img in images:
        if img["src"] and not img["src"].startswith("/"):
            img["src"] = "/media/" + img["src"]
    tags = list(product.tags.all().values("id", "name"))
    reviews_count = product.reviews.count()
    return {
        "id": product.pk,
        "category": product.category_id,
        "price": float(product.price),
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


def _product_full(product):
    """Serialize product to full format (for detail page)."""
    data = _product_short(product)
    data["fullDescription"] = product.full_description
    data["specifications"] = list(
        product.specifications.all().values("name", "value")
    )
    data["reviews"] = list(
        product.reviews.all().values("author", "email", "text", "rate", "date")
    )
    for r in data["reviews"]:
        if r["date"]:
            r["date"] = r["date"].strftime("%Y-%m-%d %H:%M")
    return data


def _category_data(category):
    """Serialize category with subcategories."""
    image = {"src": "", "alt": ""}
    if category.image:
        src = category.image.url if category.image else ""
        image = {"src": src, "alt": category.title}
    subcats = []
    for sub in Category.objects.filter(parent=category, is_active=True):
        sub_image = {"src": "", "alt": ""}
        if sub.image:
            sub_image = {"src": sub.image.url, "alt": sub.title}
        subcats.append(
            {
                "id": sub.pk,
                "title": sub.title,
                "image": sub_image,
            }
        )
    return {
        "id": category.pk,
        "title": category.title,
        "image": image,
        "subcategories": subcats,
    }


def _parse_json_body(request):
    """Parse JSON from request body."""
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return {}


def _get_basket(request):
    """Get basket dict from session: {product_id_str: count}."""
    return request.session.get("basket", {})


def _set_basket(request, basket):
    """Save basket to session."""
    request.session["basket"] = basket
    request.session.modified = True


def _basket_response(request):
    """Build basket response as list of products with count."""
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
# Auth
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class SignInView(View):
    def post(self, request):
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
    def post(self, request):
        data = _parse_json_body(request)
        name = data.get("name", "")
        username = data.get("username", "")
        password = data.get("password", "")
        if User.objects.filter(username=username).exists():
            return JsonResponse(
                {"error": "User already exists"}, status=500
            )
        user = User.objects.create_user(
            username=username, password=password, first_name=name
        )
        Profile.objects.create(user=user, full_name=name)
        login(request, user)
        return JsonResponse({}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class SignOutView(View):
    def post(self, request):
        logout(request)
        return JsonResponse({}, status=200)


# ═══════════════════════════════════════════════
# Categories
# ═══════════════════════════════════════════════


class CategoryListView(View):
    def get(self, request):
        categories = Category.objects.filter(parent__isnull=True, is_active=True)
        result = [_category_data(cat) for cat in categories]
        return JsonResponse(result, safe=False)


# ═══════════════════════════════════════════════
# Catalog (with filters, sort, pagination)
# ═══════════════════════════════════════════════


class CatalogView(View):
    def get(self, request):
        # Filters
        name = request.GET.get("filter[name]", "")
        min_price = request.GET.get("filter[minPrice]")
        max_price = request.GET.get("filter[maxPrice]")
        free_delivery = request.GET.get("filter[freeDelivery]", "false")
        available = request.GET.get("filter[available]", "false")
        category_id = request.GET.get("category")
        tags_list = request.GET.getlist("tags[]")

        # Sort
        sort_field = request.GET.get("sort", "date")
        sort_type = request.GET.get("sortType", "dec")

        # Pagination
        current_page = int(request.GET.get("currentPage", 1))
        limit = int(request.GET.get("limit", 20))

        qs = Product.objects.all()

        # Apply filters
        if name:
            qs = qs.filter(title__icontains=name)
        if min_price:
            qs = qs.filter(price__gte=float(min_price))
        if max_price:
            qs = qs.filter(price__lte=float(max_price))
        if free_delivery == "true":
            qs = qs.filter(free_delivery=True)
        if available == "true":
            qs = qs.filter(count__gt=0)
        if category_id:
            # Include subcategories
            cat_ids = [int(category_id)]
            sub_cats = Category.objects.filter(parent_id=int(category_id))
            cat_ids.extend(sub_cats.values_list("id", flat=True))
            qs = qs.filter(category_id__in=cat_ids)
        if tags_list:
            qs = qs.filter(tags__id__in=tags_list).distinct()

        # Sort
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

        # Pagination
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
# Popular products (top 8 by sort_index, then purchases_count)
# ═══════════════════════════════════════════════


class PopularProductsView(View):
    def get(self, request):
        products = Product.objects.order_by("sort_index", "-purchases_count")[:8]
        result = [_product_short(p) for p in products]
        return JsonResponse(result, safe=False)


# ═══════════════════════════════════════════════
# Limited edition products (up to 16)
# ═══════════════════════════════════════════════


class LimitedProductsView(View):
    def get(self, request):
        products = Product.objects.filter(limited_edition=True)[:16]
        result = [_product_short(p) for p in products]
        return JsonResponse(result, safe=False)


# ═══════════════════════════════════════════════
# Sales (with pagination)
# ═══════════════════════════════════════════════


class SalesView(View):
    def get(self, request):
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
# Banners (3 featured categories/products)
# ═══════════════════════════════════════════════


class BannersView(View):
    def get(self, request):
        # Return random products from active categories for banners
        products = list(Product.objects.filter(count__gt=0).select_related("category")[:50])
        if len(products) > 3:
            products = random.sample(products, 3)
        result = [_product_short(p) for p in products]
        # Add category field for banner link
        for i, p in enumerate(products):
            result[i]["category"] = p.category_id
        return JsonResponse(result, safe=False)


# ═══════════════════════════════════════════════
# Product detail
# ═══════════════════════════════════════════════


class ProductDetailView(View):
    def get(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)
        return JsonResponse(_product_full(product))


# ═══════════════════════════════════════════════
# Product reviews
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class ProductReviewView(View):
    def post(self, request, pk):
        try:
            product = Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        data = _parse_json_body(request)
        Review.objects.create(
            product=product,
            author=data.get("author", "Anonymous"),
            email=data.get("email", ""),
            text=data.get("text", ""),
            rate=int(data.get("rate", 5)),
        )
        # Recalculate rating
        reviews = product.reviews.all()
        if reviews.exists():
            avg = sum(r.rate for r in reviews) / reviews.count()
            product.rating = round(avg, 1)
            product.save(update_fields=["rating"])

        # Return all reviews
        all_reviews = list(reviews.values("author", "email", "text", "rate", "date"))
        for r in all_reviews:
            if r["date"]:
                r["date"] = r["date"].strftime("%Y-%m-%d %H:%M")
        return JsonResponse(all_reviews, safe=False)


# ═══════════════════════════════════════════════
# Tags
# ═══════════════════════════════════════════════


class TagsView(View):
    def get(self, request):
        category_id = request.GET.get("category")
        if category_id:
            tags = Tag.objects.filter(products__category_id=int(category_id)).distinct()
        else:
            tags = Tag.objects.all()
        result = list(tags.values("id", "name"))
        return JsonResponse(result, safe=False)


# ═══════════════════════════════════════════════
# Basket (session-based)
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class BasketView(View):
    def get(self, request):
        return JsonResponse(_basket_response(request), safe=False)

    def post(self, request):
        data = _parse_json_body(request)
        product_id = str(data.get("id", ""))
        count = int(data.get("count", 1))
        basket = _get_basket(request)
        basket[product_id] = basket.get(product_id, 0) + count
        _set_basket(request, basket)
        return JsonResponse(_basket_response(request), safe=False)

    def delete(self, request):
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
# Orders
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class OrdersView(View):
    def get(self, request):
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

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Auth required"}, status=403)

        basket_items = _basket_response(request)
        if not basket_items:
            return JsonResponse({"error": "Basket is empty"}, status=400)

        # Create order with products from basket
        profile = getattr(request.user, "profile", None)
        order = Order.objects.create(
            user=request.user,
            full_name=profile.full_name if profile else request.user.username,
            email=request.user.email,
            phone=profile.phone if profile else "",
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

        # Clear basket
        _set_basket(request, {})

        return JsonResponse({"orderId": order.pk})


@method_decorator(csrf_exempt, name="dispatch")
class OrderDetailView(View):
    def get(self, request, pk):
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

    def post(self, request, pk):
        """Confirm order — update delivery/payment info, calculate total with delivery."""
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

        # Recalculate total with delivery cost
        settings = SiteSettings.load()
        products_total = sum(
            float(item.price) * item.count for item in order.items.all()
        )

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
# Payment (fake payment service)
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class PaymentView(View):
    def post(self, request, pk):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return JsonResponse({"error": "Not found"}, status=404)

        data = _parse_json_body(request)
        number = data.get("number", "").replace(" ", "")

        # Validate: must be digits, max 8, even number
        if not number.isdigit() or len(number) > 8:
            return JsonResponse({"error": "Invalid card number"}, status=400)

        card_number = int(number)
        if card_number % 2 != 0:
            return JsonResponse({"error": "Card number must be even"}, status=400)

        # Fake payment logic:
        # even and NOT ending in 0 -> success
        # even and ending in 0 -> random error
        if card_number % 10 == 0:
            errors = [
                "Недостаточно средств",
                "Банк отклонил операцию",
                "Превышен лимит",
                "Ошибка обработки платежа",
            ]
            order.status = Order.Status.PAYMENT_ERROR
            order.payment_error = random.choice(errors)
            order.save(update_fields=["status", "payment_error"])
            return JsonResponse({"error": order.payment_error}, status=400)
        else:
            order.status = Order.Status.PAID
            order.payment_error = None
            order.save(update_fields=["status", "payment_error"])

            # Increase purchases_count for products
            for item in order.items.select_related("product").all():
                item.product.purchases_count += item.count
                item.product.save(update_fields=["purchases_count"])

            return JsonResponse({}, status=200)


# ═══════════════════════════════════════════════
# Profile
# ═══════════════════════════════════════════════


@method_decorator(csrf_exempt, name="dispatch")
class ProfileView(View):
    def get(self, request):
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

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Auth required"}, status=403)

        data = _parse_json_body(request)
        profile, _ = Profile.objects.get_or_create(user=request.user)

        profile.full_name = data.get("fullName", profile.full_name)
        phone = data.get("phone", profile.phone)
        email = data.get("email", request.user.email)

        # Check uniqueness
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
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Auth required"}, status=403)

        data = _parse_json_body(request)
        current_password = data.get("currentPassword", "")
        new_password = data.get("newPassword", "")

        if not request.user.check_password(current_password):
            return JsonResponse({"error": "Wrong current password"}, status=400)

        request.user.set_password(new_password)
        request.user.save()
        # Re-login so session doesn't break
        login(request, request.user)
        return JsonResponse({}, status=200)


@method_decorator(csrf_exempt, name="dispatch")
class AvatarView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Auth required"}, status=403)

        avatar_file = request.FILES.get("avatar")
        if not avatar_file:
            return JsonResponse({"error": "No file"}, status=400)

        # Check size (2 MB)
        if avatar_file.size > 2 * 1024 * 1024:
            return JsonResponse({"error": "File too large (max 2 MB)"}, status=400)

        profile, _ = Profile.objects.get_or_create(user=request.user)
        profile.avatar = avatar_file
        profile.save(update_fields=["avatar"])
        return JsonResponse(
            {"src": profile.avatar.url, "alt": profile.full_name}
        )
