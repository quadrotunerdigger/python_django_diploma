"""
Link existing images from media/products/ to Product records.
Walks 3-level structure: media/products/<ParentCat>/<SubCat>/<Product>/preview|images/

Usage: python manage.py link_images
"""
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from shopapp.models import Product, ProductImage


# Map product folder name -> product title in DB
FOLDER_TO_TITLE = {
    # Electronics / Smartphones
    "iPhone_15_Pro": "iPhone 15 Pro",
    "Samsung_Galaxy_S24": "Samsung Galaxy S24",
    # Electronics / Headphones
    "Sony_WH-1000XM5": "Sony WH-1000XM5",
    # Electronics / Audio speakers
    "JBL_Charge_5": "JBL Charge 5",
    "Яндекс_Станция_Макс": "Яндекс Станция Макс",
    # Electronics / Cameras
    "Canon_EOS_R6_Mark_II": "Canon EOS R6 Mark II",
    "Sony_Alpha_A7_IV": "Sony Alpha A7 IV",
    # Home appliances / Washing machines
    "LG_F2V5": "Стиральная машина LG F2V5",
    # Home appliances / Refrigerators
    "Samsung_RF50": "Холодильник Samsung RF50",
    # Home appliances / Vacuum cleaners
    "Dyson_V15_Detect": "Dyson V15 Detect",
    "Roborock_S8": "Робот-пылесос Roborock S8",
    # Home appliances / Electric stoves and furnaces
    "Electrolux_EKC954907X": "Electrolux EKC954907X",
    "Gorenje_EC5241SG": "Gorenje EC5241SG",
    # Home appliances / Microwave ovens
    "Samsung_ME88SUG": "Samsung ME88SUG",
    "LG_MS2595CIS": "LG MS2595CIS",
    # Home appliances / Mixers and blenders
    "Bosch_MSM67170": "Bosch MSM67170",
    "KitchenAid_5KSM175PS": "KitchenAid 5KSM175PS",
    # Home appliances / Table lamps
    "Xiaomi_Mi_LED_Desk_Lamp_1S": "Xiaomi Mi LED Desk Lamp 1S",
    "Philips_Hue_Go": "Philips Hue Go",
    # Home appliances / Teapots
    "Bosch_TWK8611P": "Bosch TWK8611P",
    "Xiaomi_Mi_Smart_Kettle_Pro": "Xiaomi Mi Smart Kettle Pro",
    # Computers / Video cards
    "NVIDIA_RTX_4090": "NVIDIA RTX 4090",
    "NVIDIA_RTX_4070": "NVIDIA RTX 4070",
    # Computers / Processors
    "AMD_Ryzen_9_7950X": "AMD Ryzen 9 7950X",
    "Intel_Core_i9-14900K": "Intel Core i9-14900K",
    # Computers / Monitors
    "ASUS_ROG_Swift_PG32": "ASUS ROG Swift PG32",
    # Computers / Laptops and tablets / Notebooks
    "MacBook_Air_M3": "MacBook Air M3",
    "Lenovo_ThinkPad_X1": "Lenovo ThinkPad X1",
    "iPad_Pro_12.9": "iPad Pro 12.9",
    "Dell_XPS_15": "Dell XPS 15",
}


class Command(BaseCommand):
    help = "Link existing images from media/products/ to Product records"

    def handle(self, *args, **options):
        media_root = settings.MEDIA_ROOT
        products_dir = os.path.join(media_root, "products")

        if not os.path.exists(products_dir):
            self.stdout.write(self.style.ERROR(f"Not found: {products_dir}"))
            return

        linked = 0
        skipped = 0

        # Recursively find all 'preview' and 'images' folders
        for root, dirs, files in os.walk(products_dir):
            basename = os.path.basename(root)
            if basename not in ("preview", "images"):
                continue

            is_preview = basename == "preview"
            # Parent of preview/images is the product folder
            product_folder = os.path.basename(os.path.dirname(root))
            title = FOLDER_TO_TITLE.get(product_folder)

            if not title:
                # Only warn once per product folder
                if is_preview:
                    self.stdout.write(
                        self.style.WARNING(f"  No mapping: {product_folder}")
                    )
                    skipped += 1
                continue

            try:
                product = Product.all_objects.get(title=title)
            except Product.DoesNotExist:
                if is_preview:
                    self.stdout.write(
                        self.style.WARNING(f"  Not in DB: {title}")
                    )
                    skipped += 1
                continue

            for fn in sorted(files):
                if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    continue
                # Relative path from MEDIA_ROOT
                abs_path = os.path.join(root, fn)
                rel_path = os.path.relpath(abs_path, media_root)

                if not ProductImage.objects.filter(
                    product=product, src=rel_path
                ).exists():
                    ProductImage.objects.create(
                        product=product,
                        src=rel_path,
                        alt=title,
                        is_preview=is_preview,
                    )
                    linked += 1
                    tag = "preview" if is_preview else "image"
                    self.stdout.write(f"  + [{tag}] {rel_path}")

        self.stdout.write(
            self.style.SUCCESS(f"Done! Linked {linked}, skipped {skipped}.")
        )
