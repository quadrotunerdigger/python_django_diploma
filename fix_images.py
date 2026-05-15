import os
from django.conf import settings
from shopapp.models import Product, ProductImage

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

products_dir = os.path.join(settings.MEDIA_ROOT, "products")
linked = 0

for cat in os.listdir(products_dir):
    cat_path = os.path.join(products_dir, cat)
    if not os.path.isdir(cat_path):
        continue
    for prod_folder in os.listdir(cat_path):
        prod_path = os.path.join(cat_path, prod_folder)
        if not os.path.isdir(prod_path):
            continue
        title = FOLDER_TO_PRODUCT.get(prod_folder)
        if not title:
            print(f"SKIP: no mapping for {prod_folder}")
            continue
        try:
            product = Product.all_objects.get(title=title)
        except Product.DoesNotExist:
            print(f"SKIP: product not found: {title}")
            continue
        for subfolder, is_preview in [("preview", True), ("images", False)]:
            sf_path = os.path.join(prod_path, subfolder)
            if not os.path.isdir(sf_path):
                continue
            for fn in sorted(os.listdir(sf_path)):
                if not fn.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    continue
                rel_path = "products/" + cat + "/" + prod_folder + "/" + subfolder + "/" + fn
                if not ProductImage.objects.filter(product=product, src=rel_path).exists():
                    ProductImage.objects.create(
                        product=product,
                        src=rel_path,
                        alt=title,
                        is_preview=is_preview,
                    )
                    linked += 1
                    print("  + " + rel_path)

print(f"Done! Linked {linked} images total.")
