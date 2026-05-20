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

        # Бытовая техника (icon 3)
        bt, _ = Category.objects.get_or_create(
            title="Бытовая техника", defaults={"is_active": True, "sort_index": 1}
        )
        for name in [
            "Стиральные машины", "Пылесосы", "Холодильники",
            "Электрические плиты и печи", "Печи СВЧ",
            "Миксеры и блендеры", "Настольные лампы", "Чайники",
        ]:
            Category.objects.get_or_create(
                title=name, defaults={"parent": bt, "is_active": True, "sort_index": 0}
            )

        # Электроника (icon 5)
        el, _ = Category.objects.get_or_create(
            title="Электроника", defaults={"is_active": True, "sort_index": 2}
        )
        for name in ["Смартфоны", "Наушники", "Колонки", "Фотоаппараты"]:
            Category.objects.get_or_create(
                title=name, defaults={"parent": el, "is_active": True, "sort_index": 0}
            )

        # Компьютеры и комплектующие (icon 1)
        comp, _ = Category.objects.get_or_create(
            title="Компьютеры и комплектующие",
            defaults={"is_active": True, "sort_index": 3},
        )
        for name in ["Видеокарты", "Процессоры", "Мониторы", "Ноутбуки и планшеты"]:
            Category.objects.get_or_create(
                title=name, defaults={"parent": comp, "is_active": True, "sort_index": 0}
            )

        # Deactivate old categories
        for old in ["Компьютеры", "Ноутбуки", "Планшеты"]:
            Category.objects.filter(title=old).update(is_active=False)

        # ── Products ──────────────────────────────
        product_data = [
            # Электроника -> Смартфоны
            ("iPhone 15 Pro", "Смартфон Apple iPhone 15 Pro 256GB", "Смартфоны", 89990, False),
            ("Samsung Galaxy S24", "Флагманский смартфон Samsung Galaxy S24 128GB", "Смартфоны", 74990, False),
            # Электроника -> Наушники
            ("Sony WH-1000XM5", "Беспроводные наушники с шумоподавлением", "Наушники", 29990, False),
            # Электроника -> Колонки
            ("JBL Charge 5", "Портативная колонка JBL Charge 5 с защитой IP67", "Колонки", 12990, False),
            ("Яндекс Станция Макс", "Умная колонка с Алисой и LED-дисплеем", "Колонки", 17990, False),
            # Электроника -> Фотоаппараты
            ("Canon EOS R6 Mark II", "Полнокадровая беззеркальная камера Canon", "Фотоаппараты", 189990, True),
            ("Sony Alpha A7 IV", "Беззеркальная камера Sony 33 Мп", "Фотоаппараты", 179990, True),
            # Бытовая техника -> Холодильники
            ("Холодильник Samsung RF50", "Двухкамерный холодильник Samsung RF50A5202S9", "Холодильники", 74990, False),
            # Бытовая техника -> Стиральные машины
            ("Стиральная машина LG F2V5", "Стиральная машина LG F2V5HS2S с паром", "Стиральные машины", 44990, False),
            # Бытовая техника -> Пылесосы
            ("Dyson V15 Detect", "Беспроводной пылесос Dyson V15 Detect Absolute", "Пылесосы", 59990, False),
            ("Робот-пылесос Roborock S8", "Умный робот-пылесос с лидаром", "Пылесосы", 39990, False),
            # Бытовая техника -> Электрические плиты и печи
            ("Electrolux EKC954907X", "Электрическая плита Electrolux со стеклокерамикой", "Электрические плиты и печи", 54990, False),
            ("Gorenje EC5241SG", "Электрическая плита Gorenje с грилем", "Электрические плиты и печи", 32990, False),
            # Бытовая техника -> Печи СВЧ
            ("Samsung ME88SUG", "Микроволновая печь Samsung 23л с грилем", "Печи СВЧ", 11990, False),
            ("LG MS2595CIS", "Микроволновая печь LG NeoChef 25л", "Печи СВЧ", 13990, False),
            # Бытовая техника -> Миксеры и блендеры
            ("Bosch MSM67170", "Погружной блендер Bosch ErgoMixx 750Вт", "Миксеры и блендеры", 5990, False),
            ("KitchenAid 5KSM175PS", "Планетарный миксер KitchenAid Artisan 4.8л", "Миксеры и блендеры", 49990, False),
            # Бытовая техника -> Настольные лампы
            ("Xiaomi Mi LED Desk Lamp 1S", "Настольная лампа Xiaomi с регулировкой яркости", "Настольные лампы", 2990, False),
            ("Philips Hue Go", "Портативная настольная лампа Philips с RGB", "Настольные лампы", 7990, False),
            # Бытовая техника -> Чайники
            ("Bosch TWK8611P", "Электрический чайник Bosch Styline 1.5л", "Чайники", 5490, False),
            ("Xiaomi Mi Smart Kettle Pro", "Умный чайник Xiaomi с контролем температуры", "Чайники", 3490, False),
            # Компьютеры -> Видеокарты
            ("NVIDIA RTX 4090", "Видеокарта NVIDIA GeForce RTX 4090 24GB", "Видеокарты", 149990, True),
            ("NVIDIA RTX 4070", "Видеокарта NVIDIA GeForce RTX 4070 12GB", "Видеокарты", 54990, False),
            # Компьютеры -> Процессоры
            ("AMD Ryzen 9 7950X", "Процессор AMD Ryzen 9 7950X 16 ядер", "Процессоры", 44990, False),
            ("Intel Core i9-14900K", "Процессор Intel Core i9-14900K 24 ядра", "Процессоры", 49990, False),
            # Компьютеры -> Мониторы
            ("ASUS ROG Swift PG32", "Игровой монитор ASUS 32 дюйма 4K 144Hz", "Мониторы", 89990, False),
            # Компьютеры -> Ноутбуки и планшеты
            ("MacBook Air M3", "Ноутбук Apple MacBook Air 13 M3 8/256GB", "Ноутбуки и планшеты", 109990, True),
            ("Lenovo ThinkPad X1", "Бизнес-ноутбук Lenovo ThinkPad X1 Carbon Gen 11", "Ноутбуки и планшеты", 124990, True),
            ("iPad Pro 12.9", "Планшет Apple iPad Pro 12.9 M2 128GB Wi-Fi", "Ноутбуки и планшеты", 99990, True),
            ("Dell XPS 15", "Ноутбук Dell XPS 15 9530 i7/16GB/512GB", "Ноутбуки и планшеты", 134990, False),
        ]

        products = []
        for i, (title, desc, cat_name, price, limited) in enumerate(product_data):
            try:
                category = Category.objects.get(title=cat_name, is_active=True)
            except Category.DoesNotExist:
                self.stdout.write(self.style.WARNING(f"  Category not found: {cat_name}"))
                continue

            product, created = Product.objects.get_or_create(
                title=title,
                defaults={
                    "category": category,
                    "description": desc,
                    "full_description": (
                        f"<p>{desc}.</p>"
                        f"<p>Высокое качество, гарантия от производителя. "
                        f"Доставка по всей России.</p>"
                    ),
                    "price": Decimal(str(price)),
                    "count": random.randint(5, 100),
                    "free_delivery": price > 50000,
                    "limited_edition": limited,
                    "sort_index": i,
                    "rating": Decimal(str(round(random.uniform(3.5, 5.0), 1))),
                    "purchases_count": random.randint(10, 500),
                },
            )
            if created:
                product.tags.add(*random.sample(tags, k=min(3, len(tags))))
                specs = [
                    ("Производитель", title.split()[0]),
                    ("Гарантия", f"{random.choice([12, 24, 36])} мес."),
                ]
                for sn, sv in specs:
                    Specification.objects.create(product=product, name=sn, value=sv)
            products.append(product)

        # ── Reviews ───────────────────────────────
        authors = ["Иван", "Мария", "Алексей", "Ольга", "Дмитрий", "Анна"]
        texts = [
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
                        author=random.choice(authors),
                        email=f"{random.choice(authors).lower()}@test.ru",
                        text=random.choice(texts),
                        rate=random.randint(3, 5),
                    )

        # ── Sales ─────────────────────────────────
        now = timezone.now().date()
        for product in random.sample(products, min(7, len(products))):
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
                    username=username, password="123456",
                    email=f"buyer{i}@test.ru", first_name=f"Покупатель {i}",
                )
                user.groups.add(buyer_group)
                Profile.objects.get_or_create(
                    user=user,
                    defaults={"full_name": f"Покупатель Тестовый {i}", "phone": f"+7900000000{i}"},
                )

        # ── Demo orders ───────────────────────────
        for buyer in User.objects.filter(groups__name="Покупатель"):
            if not Order.objects.filter(user=buyer).exists():
                prof = getattr(buyer, "profile", None)
                order = Order.objects.create(
                    user=buyer,
                    full_name=prof.full_name if prof else buyer.username,
                    email=buyer.email,
                    phone=prof.phone if prof and prof.phone else "",
                    delivery_type=random.choice(["ordinary", "express"]),
                    payment_type=random.choice(["online", "someone"]),
                    status=random.choice(["paid", "accepted", "created"]),
                    city="Москва", address="ул. Тестовая, д. 1",
                )
                total = Decimal("0")
                for p in random.sample(products, min(3, len(products))):
                    c = random.randint(1, 3)
                    OrderItem.objects.create(order=order, product=p, price=p.price, count=c)
                    total += p.price * c
                order.total_cost = total
                order.save(update_fields=["total_cost"])

        self.stdout.write(self.style.SUCCESS(
            f"Done! {len(products)} products, "
            f"{Category.objects.filter(is_active=True).count()} categories, "
            f"{Review.objects.count()} reviews, "
            f"{Sale.objects.count()} sales, "
            f"{Order.objects.count()} orders."
        ))
