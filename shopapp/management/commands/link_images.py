"""
Management command to link existing images from media/products/ to Product records.
Scans media/products/<Category>/<Product_name>/preview/ and .../images/
and creates ProductImage records.

Usage: python manage.py link_images
"""
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from shopapp.models import Product, ProductImage


# Map folder names to product titles
FOLDER_TO_PRODUCT = {
    "iPhone_15_Pro": "iPhone 15 Pro",
    "Samsung_Galaxy_S24": "Samsung Galaxy S24",
    "MacBook_Air_M3": "MacBook Air M3",
    "Lenovo_ThinkPad_X1": "Lenovo ThinkPad X1",
    "iPad_Pro_12.9": "iPad Pro 12.9",
    "Samsung_RF50": "Холодильник Samsung RF50",
    "LG_F2V5": "Стиральная машина LG F2V5",
    "Dyson_V15_Detect": "Dyson V15 Detect",
    "NVIDIA_RTX_4090": "NVIDIA RTX 4090",
    "AMD_Ryzen_9_7950X": "AMD Ryzen 9 7950X",
    "ASUS_ROG_Swift_PG32": "ASUS ROG Swift PG32",
    "Intel_Core_i9-14900K": "Intel Core i9-14900K",
    "Dell_XPS_15": "Dell XPS 15",
    "Sony_WH-1000XM5": "Sony WH-1000XM5",
    "Roborock_S8": "Робот-пылесос Roborock S8",
    "NVIDIA_RTX_4070": "NVIDIA RTX 4070",
}


class Command(BaseCommand):
    help = "Link existing images from media/products/ to Product records"

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        products_dir = os.path.join(media_root, "products")

        if not os.path.exists(products_dir):
            self.stdout.write(self.style.ERROR(f"Directory not found: {products_dir}"))
            return

        linked = 0
        skipped = 0

        # Walk through category folders
        for category_folder in os.listdir(products_dir):
            category_path = os.path.join(products_dir, category_folder)
            if not os.path.isdir(category_path):
                continue

            # Walk through product folders
            for product_folder in os.listdir(category_path):
                product_path = os.path.join(category_path, product_folder)
                if not os.path.isdir(product_path):
                    continue

                # Find matching product
                product_title = FOLDER_TO_PRODUCT.get(product_folder)
                if not product_title:
                    self.stdout.write(
                        self.style.WARNING(
                            f"No mapping for folder: {product_folder}"
                        )
                    )
                    skipped += 1
                    continue

                try:
                    product = Product.all_objects.get(title=product_title)
                except Product.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Product not found: {product_title}"
                        )
                    )
                    skipped += 1
                    continue

                # Process preview folder
                preview_dir = os.path.join(product_path, "preview")
                if os.path.isdir(preview_dir):
                    for filename in sorted(os.listdir(preview_dir)):
                        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                            continue
                        rel_path = os.path.join(
                            "products", category_folder, product_folder, "preview", filename
                        )
                        if not ProductImage.objects.filter(product=product, src=rel_path).exists():
                            ProductImage.objects.create(
                                product=product,
                                src=rel_path,
                                alt=product.title,
                                is_preview=True,
                            )
                            linked += 1
                            self.stdout.write(f"  + preview: {rel_path}")

                # Process images folder
                images_dir = os.path.join(product_path, "images")
                if os.path.isdir(images_dir):
                    for filename in sorted(os.listdir(images_dir)):
                        if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                            continue
                        rel_path = os.path.join(
                            "products", category_folder, product_folder, "images", filename
                        )
                        if not ProductImage.objects.filter(product=product, src=rel_path).exists():
                            ProductImage.objects.create(
                                product=product,
                                src=rel_path,
                                alt=product.title,
                                is_preview=False,
                            )
                            linked += 1
                            self.stdout.write(f"  + image: {rel_path}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Linked {linked} images, skipped {skipped} folders."
            )
        )
