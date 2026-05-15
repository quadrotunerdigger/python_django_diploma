"""
Management command to populate the database with demo data.
Usage: python manage.py populate_demo
"""
import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User, Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from shopapp.models import (
    Category,
    Product,
    ProductImage,
    Specification,
    Tag,
    Review,
    Sale,
    Profile,
    Order,
    OrderItem,
)


class Command(BaseCommand):
    help = "Populate the database with demo data for testing"

    def handle(self, *args, **options):
        self.stdout.write("Creating demo data...")

        # ── Tags ──────────────────────────────────
        tag_names = [
            "Gaming", "Office", "Budget", "Premium", "Новинка",
            "Хит продаж", "Акция", "Рекомендуем",
        ]
        tags = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(name=name)
            tags.append(tag)

        # ── Categories ────────────────────────────
        categories_data = {
            "Электроника": ["Смартфоны", "Ноутбуки", "Планшеты"],
            "Бытовая техника": ["Холодильники", "Стиральные машины", "Пылесосы"],
            "Компьютеры": ["Видеокарты", "Процессоры", "Мониторы"],
        }
        all_subcats = []
        for parent_name, children in categories_data.items():
            parent, _ = Category.objects.get_or_create(
                title=parent_name,
                defaults={"is_active": True, "sort_index": 0},
            )
            for child_name in children:
                child, _ = Category.objects.get_or_create(
                    title=child_name,
                    defaults={"parent": parent, "is_active": True, "sort_index": 0},
                )
                all_subcats.append(child)

        # ── Products ──────────────────────────────
        product_templates = [
            ("iPhone 15 Pro", "Смартфон Apple iPhone 15 Pro", "Электроника"),
            ("Samsung Galaxy S24", "Флагманский смартфон Samsung", "Электроника"),
            ("MacBook Air M3", "Ноутбук Apple MacBook Air", "Электроника"),
            ("Lenovo ThinkPad X1", "Бизнес-ноутбук Lenovo", "Электроника"),
            ("iPad Pro 12.9", "Планшет Apple iPad Pro", "Электроника"),
            ("Холодильник Samsung RF50", "Двухкамерный холодильник", "Бытовая техника"),
            ("Стиральная машина LG F2V5", "Стиральная машина с паром", "Бытовая техника"),
            ("Dyson V15 Detect", "Беспроводной пылесос", "Бытовая техника"),
            ("NVIDIA RTX 4090", "Видеокарта NVIDIA GeForce RTX 4090", "Компьютеры"),
            ("AMD Ryzen 9 7950X", "Процессор AMD Ryzen 9", "Компьютеры"),
            ("ASUS ROG Swift PG32", "Игровой монитор 32 дюйма", "Компьютеры"),
            ("Intel Core i9-14900K", "Процессор Intel Core i9", "Компьютеры"),
            ("Dell XPS 15", "Ноутбук Dell XPS 15", "Электроника"),
            ("Sony WH-1000XM5", "Наушники с шумоподавлением", "Электроника"),
            ("Робот-пылесос Roborock S8", "Умный робот-пылесос", "Бытовая техника"),
            ("NVIDIA RTX 4070", "Видеокарта среднего класса", "Компьютеры"),
        ]

        products = []
        for i, (title, desc, cat_name) in enumerate(product_templates):
            parent_cat = Category.objects.get(title=cat_name)
            subcats = list(Category.objects.filter(parent=parent_cat))
            category = random.choice(subcats) if subcats else parent_cat

            price = Decimal(random.randint(5000, 200000))
            product, created = Product.objects.get_or_create(
                title=title,
                defaults={
                    "category": category,
                    "description": desc,
                    "full_description": f"<p>{desc}. Подробное описание товара с характеристиками и преимуществами.</p>"
                                        f"<p>Высокое качество сборки, гарантия от производителя.</p>",
                    "price": price,
                    "count": random.randint(0, 100),
                    "free_delivery": random.choice([True, False]),
                    "limited_edition": i < 5,  # first 5 are limited
                    "sort_index": i,
                    "rating": Decimal(str(round(random.uniform(3.0, 5.0), 1))),
                    "purchases_count": random.randint(0, 500),
                },
            )
            if created:
                product.tags.add(*random.sample(tags, k=min(3, len(tags))))
                # Specifications
                specs = [
                    ("Производитель", title.split()[0]),
                    ("Гарантия", f"{random.choice([12, 24, 36])} мес."),
                    ("Вес", f"{round(random.uniform(0.1, 15.0), 1)} кг"),
                ]
                for spec_name, spec_value in specs:
                    Specification.objects.create(
                        product=product, name=spec_name, value=spec_value
                    )
            products.append(product)

        # ── Reviews ───────────────────────────────
        reviewers = ["Иван", "Мария", "Алексей", "Ольга", "Дмитрий", "Анна"]
        review_texts = [
            "Отличный товар, рекомендую!",
            "Хорошее качество за свои деньги.",
            "Доставка быстрая, товар соответствует описанию.",
            "Есть небольшие недочёты, но в целом доволен.",
            "Превосходное качество сборки.",
            "Пользуюсь уже месяц, всё отлично работает.",
        ]
        for product in products:
            if not product.reviews.exists():
                for _ in range(random.randint(1, 4)):
                    Review.objects.create(
                        product=product,
                        author=random.choice(reviewers),
                        email=f"{random.choice(reviewers).lower()}@test.ru",
                        text=random.choice(review_texts),
                        rate=random.randint(3, 5),
                    )

        # ── Sales ─────────────────────────────────
        now = timezone.now().date()
        for product in random.sample(products, min(5, len(products))):
            if not Sale.objects.filter(product=product).exists():
                Sale.objects.create(
                    product=product,
                    sale_price=product.price * Decimal("0.7"),
                    date_from=now - timedelta(days=5),
                    date_to=now + timedelta(days=25),
                )

        # ── Demo buyers ───────────────────────────
        buyer_group, _ = Group.objects.get_or_create(name="Покупатель")
        for i in range(1, 4):
            username = f"buyer{i}"
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    password="123456",
                    email=f"buyer{i}@test.ru",
                    first_name=f"Покупатель {i}",
                )
                user.groups.add(buyer_group)
                Profile.objects.get_or_create(
                    user=user,
                    defaults={
                        "full_name": f"Покупатель Тестовый {i}",
                        "phone": f"+7900000000{i}",
                    },
                )

        # ── Demo orders ───────────────────────────
        buyers = User.objects.filter(groups__name="Покупатель")
        for buyer in buyers:
            if not Order.objects.filter(user=buyer).exists():
                profile = buyer.profile
                order = Order.objects.create(
                    user=buyer,
                    full_name=profile.full_name,
                    email=buyer.email,
                    phone=profile.phone,
                    delivery_type=random.choice(["ordinary", "express"]),
                    payment_type=random.choice(["online", "someone"]),
                    status=random.choice(["paid", "accepted", "created"]),
                    city="Москва",
                    address="ул. Тестовая, д. 1",
                )
                total = Decimal("0")
                for product in random.sample(products, min(3, len(products))):
                    count = random.randint(1, 3)
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        price=product.price,
                        count=count,
                    )
                    total += product.price * count
                order.total_cost = total
                order.save(update_fields=["total_cost"])

        self.stdout.write(self.style.SUCCESS(
            f"Done! Created {len(products)} products, "
            f"{Tag.objects.count()} tags, "
            f"{Category.objects.count()} categories, "
            f"{Review.objects.count()} reviews, "
            f"{Sale.objects.count()} sales, "
            f"{Order.objects.count()} orders."
        ))
