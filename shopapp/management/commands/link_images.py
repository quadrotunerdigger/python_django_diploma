"""
Management-команда для привязки изображений из файловой системы к товарам.

Обходит директорию ``media/products/`` с трёхуровневой структурой::

    media/products/<РодительскаяКатегория>/<Подкатегория>/<Товар>/preview/
    media/products/<РодительскаяКатегория>/<Подкатегория>/<Товар>/images/

Для каждого найденного изображения создаёт запись :class:`ProductImage`,
связывая файл с соответствующим товаром в БД. Маппинг имён папок
на названия товаров задаётся в словаре :data:`FOLDER_TO_TITLE`.

Использование::

    python manage.py link_images
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand
from shopapp.models import Product, ProductImage

#: Маппинг имени папки товара → название товара в БД.
#: Ключ — имя директории в файловой системе (с подчёркиваниями),
#: значение — точное название товара из таблицы Product.
FOLDER_TO_TITLE: dict[str, str] = {
    # Электроника / Смартфоны
    "iPhone_15_Pro": "iPhone 15 Pro",
    "Samsung_Galaxy_S24": "Samsung Galaxy S24",
    # Электроника / Наушники
    "Sony_WH-1000XM5": "Sony WH-1000XM5",
    # Электроника / Колонки
    "JBL_Charge_5": "JBL Charge 5",
    "Яндекс_Станция_Макс": "Яндекс Станция Макс",
    # Электроника / Фотоаппараты
    "Canon_EOS_R6_Mark_II": "Canon EOS R6 Mark II",
    "Sony_Alpha_A7_IV": "Sony Alpha A7 IV",
    # Бытовая техника / Стиральные машины
    "LG_F2V5": "Стиральная машина LG F2V5",
    # Бытовая техника / Холодильники
    "Samsung_RF50": "Холодильник Samsung RF50",
    # Бытовая техника / Пылесосы
    "Dyson_V15_Detect": "Dyson V15 Detect",
    "Roborock_S8": "Робот-пылесос Roborock S8",
    # Бытовая техника / Электрические плиты и печи
    "Electrolux_EKC954907X": "Electrolux EKC954907X",
    "Gorenje_EC5241SG": "Gorenje EC5241SG",
    # Бытовая техника / Печи СВЧ
    "Samsung_ME88SUG": "Samsung ME88SUG",
    "LG_MS2595CIS": "LG MS2595CIS",
    # Бытовая техника / Миксеры и блендеры
    "Bosch_MSM67170": "Bosch MSM67170",
    "KitchenAid_5KSM175PS": "KitchenAid 5KSM175PS",
    # Бытовая техника / Настольные лампы
    "Xiaomi_Mi_LED_Desk_Lamp_1S": "Xiaomi Mi LED Desk Lamp 1S",
    "Philips_Hue_Go": "Philips Hue Go",
    # Бытовая техника / Чайники
    "Bosch_TWK8611P": "Bosch TWK8611P",
    "Xiaomi_Mi_Smart_Kettle_Pro": "Xiaomi Mi Smart Kettle Pro",
    # Компьютеры / Видеокарты
    "NVIDIA_RTX_4090": "NVIDIA RTX 4090",
    "NVIDIA_RTX_4070": "NVIDIA RTX 4070",
    # Компьютеры / Процессоры
    "AMD_Ryzen_9_7950X": "AMD Ryzen 9 7950X",
    "Intel_Core_i9-14900K": "Intel Core i9-14900K",
    # Компьютеры / Мониторы
    "ASUS_ROG_Swift_PG32": "ASUS ROG Swift PG32",
    # Компьютеры / Ноутбуки и планшеты
    "MacBook_Air_M3": "MacBook Air M3",
    "Lenovo_ThinkPad_X1": "Lenovo ThinkPad X1",
    "iPad_Pro_12.9": "iPad Pro 12.9",
    "Dell_XPS_15": "Dell XPS 15",
}


class Command(BaseCommand):
    """
    Django management-команда для привязки изображений к товарам.

    Рекурсивно обходит ``media/products/``, ищет папки ``preview/``
    и ``images/``, и создаёт записи :class:`ProductImage` для найденных
    файлов изображений (.png, .jpg, .jpeg, .webp).

    Идемпотентна: пропускает уже привязанные изображения.

    Attributes:
        help: Краткое описание команды для ``python manage.py help``.
    """

    help: str = "Link existing images from media/products/ to Product records"

    def handle(self, *args, **options) -> None:
        """
        Основная логика: обход файловой системы и создание записей ProductImage.

        Алгоритм:
            1. Рекурсивно обходит ``media/products/`` через ``os.walk``.
            2. Для каждой папки ``preview/`` или ``images/`` определяет
               имя родительской папки (папка товара).
            3. По :data:`FOLDER_TO_TITLE` находит название товара в БД.
            4. Для каждого файла изображения создаёт запись ``ProductImage``
               (если такая привязка ещё не существует).

        Args:
            args: Позиционные аргументы (не используются).
            options: Именованные аргументы из командной строки (не используются).
        """
        media_root: str = settings.MEDIA_ROOT
        products_dir: str = os.path.join(media_root, "products")

        if not os.path.exists(products_dir):
            self.stdout.write(self.style.ERROR(f"Not found: {products_dir}"))
            return

        linked: int = 0
        skipped: int = 0

        # Рекурсивный обход — ищем папки 'preview' и 'images'
        for root, dirs, files in os.walk(products_dir):
            basename: str = os.path.basename(root)
            if basename not in ("preview", "images"):
                continue

            is_preview: bool = basename == "preview"
            # Родительская папка preview/images — это папка товара
            product_folder: str = os.path.basename(os.path.dirname(root))
            title: str | None = FOLDER_TO_TITLE.get(product_folder)

            if not title:
                # Предупреждение только один раз (для preview)
                if is_preview:
                    self.stdout.write(self.style.WARNING(f"  No mapping: {product_folder}"))
                    skipped += 1
                continue

            try:
                product: Product = Product.all_objects.get(title=title)
            except Product.DoesNotExist:
                if is_preview:
                    self.stdout.write(self.style.WARNING(f"  Not in DB: {title}"))
                    skipped += 1
                continue

            for fn in sorted(files):
                if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    continue
                # Относительный путь от MEDIA_ROOT
                abs_path: str = os.path.join(root, fn)
                rel_path: str = os.path.relpath(abs_path, media_root)

                if not ProductImage.objects.filter(product=product, src=rel_path).exists():
                    ProductImage.objects.create(
                        product=product,
                        src=rel_path,
                        alt=title,
                        is_preview=is_preview,
                    )
                    linked += 1
                    tag: str = "preview" if is_preview else "image"
                    self.stdout.write(f"  + [{tag}] {rel_path}")

        self.stdout.write(self.style.SUCCESS(f"Done! Linked {linked}, skipped {skipped}."))
