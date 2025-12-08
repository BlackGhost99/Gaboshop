import os
import sys
import django
import random
import requests
from django.core.files.base import ContentFile

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from users.models import User  # noqa: E402
from stores.models import Store, StoreCategory  # noqa: E402
from products.models import Product, ProductCategory  # noqa: E402

def download_image(url):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return ContentFile(response.content)
    except Exception as e:
        print(f"Error downloading image {url}: {e}")
    return None

def run():
    print("Starting population script...")

    # 1. Create or Get Store Manager
    manager, created = User.objects.get_or_create(
        phone='+24100000001',
        defaults={
            'first_name': 'Jean',
            'last_name': 'Gerant',
            'user_type': 'store_manager',
            'email': 'gerant@gaboshop.ga',
            'is_active': True
        }
    )
    if created:
        manager.set_password('password123')
        manager.save()
        print(f"Created Manager: {manager.phone}")
    else:
        print(f"Found Manager: {manager.phone}")

    # 2. Create or Get Store Category
    store_cat, _ = StoreCategory.objects.get_or_create(name="Supermarché")

    # 3. Create or Get Store
    store, created = Store.objects.get_or_create(
        name="Supermarché Prix Import",
        defaults={
            'manager': manager,
            'category': store_cat,
            'phone': '+24101020304',
            'address': 'Centre Ville',
            'city': 'Libreville',
            'zone': 'Centre',
            'commission_rate': 10.0
        }
    )
    print(f"Store: {store.name}")

    # 4. Create Product Categories
    categories = ['Fruits & Légumes', 'Viandes & Poissons', 'Épicerie', 'Boissons']
    db_categories = {}
    for cat_name in categories:
        cat, _ = ProductCategory.objects.get_or_create(store=store, name=cat_name)
        db_categories[cat_name] = cat
        print(f"Category: {cat.name}")

    # 5. Create Products with Images
    products_data = [
        {
            'name': 'Tomates Fraîches (kg)',
            'category': 'Fruits & Légumes',
            'price': 1500,
            'image_url': 'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=500&q=80'
        },
        {
            'name': 'Poulet Entier (1.2kg)',
            'category': 'Viandes & Poissons',
            'price': 3500,
            'compare_price': 4000,
            'image_url': 'https://images.unsplash.com/photo-1587593810167-a84920ea0781?w=500&q=80'
        },
        {
            'name': 'Riz Parfumé (5kg)',
            'category': 'Épicerie',
            'price': 4500,
            'image_url': 'https://images.unsplash.com/photo-1586201375761-83865001e31c?w=500&q=80'
        },
        {
            'name': 'Jus d\'Orange (1L)',
            'category': 'Boissons',
            'price': 1200,
            'image_url': 'https://images.unsplash.com/photo-1600271886742-f049cd451bba?w=500&q=80'
        },
        {
            'name': 'Bananes Douces (kg)',
            'category': 'Fruits & Légumes',
            'price': 800,
            'image_url': 'https://images.unsplash.com/photo-1571771896612-e63411190f78?w=500&q=80'
        },
        {
            'name': 'Côtes de Porc (kg)',
            'category': 'Viandes & Poissons',
            'price': 4200,
            'image_url': 'https://images.unsplash.com/photo-1602498456745-e9503b30470b?w=500&q=80'
        }
    ]

    for p_data in products_data:
        product, created = Product.objects.get_or_create(
            store=store,
            name=p_data['name'],
            defaults={
                'category': db_categories[p_data['category']],
                'price': p_data['price'],
                'compare_price': p_data.get('compare_price'),
                'description': f"Délicieux {p_data['name']} de qualité supérieure.",
                'stock': random.randint(10, 100),
                'is_available': True
            }
        )
        
        if created:
            print(f"Created Product: {product.name}")
            # Download and save image
            image_content = download_image(p_data['image_url'])
            if image_content:
                filename = f"{product.name.lower().replace(' ', '_')}.jpg"
                product.image.save(filename, image_content, save=True)
                print(f"  - Image saved for {product.name}")
        else:
            print(f"Product already exists: {product.name}")

    print("Population complete!")

if __name__ == '__main__':
    run()
