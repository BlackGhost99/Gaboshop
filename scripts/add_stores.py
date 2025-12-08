import os
import sys
import django
import requests
from django.core.files.base import ContentFile

def setup_django():
    # Setup Django environment
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
    django.setup()

def download_image(query):
    # Using unsplash source for random images based on query
    url = f"https://source.unsplash.com/random/800x600/?{query}"
    # Since source.unsplash.com is deprecated/redirects, let's use a direct search or specific IDs if possible, 
    # but for a script, let's try a reliable placeholder service or just generic unsplash IDs if we knew them.
    # Actually, let's use specific reliable URLs or just try the redirect.
    # Better: Use Lorem Picsum or similar if query doesn't matter, but we want context.
    # Let's try to use the same method as populate_db.py if it worked, or just use a list of known good URLs.
    
    # Fallback to a simple reliable image if dynamic fetch fails
    try:
        # Using a different service that supports keywords might be better, but let's stick to a simple one
        # or just use a few hardcoded URLs for demo purposes.
        
        # Hardcoded map for reliability in this demo
        image_map = {
            "chicken": "https://images.unsplash.com/photo-1587593810167-a84920ea0781?auto=format&fit=crop&w=800&q=80",
            "fish": "https://images.unsplash.com/photo-1535591273668-578e31182c4f?auto=format&fit=crop&w=800&q=80",
            "tv": "https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=800&q=80",
            "washing_machine": "https://images.unsplash.com/photo-1626806775351-538af440648e?auto=format&fit=crop&w=800&q=80",
            "laptop": "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?auto=format&fit=crop&w=800&q=80",
            "mouse": "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?auto=format&fit=crop&w=800&q=80",
            "ice_cream": "https://images.unsplash.com/photo-1497034825429-c343d7c6a68f?auto=format&fit=crop&w=800&q=80",
            "vegetables": "https://images.unsplash.com/photo-1566385101042-1a0aa0c1268c?auto=format&fit=crop&w=800&q=80",
            "shirt": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?auto=format&fit=crop&w=800&q=80",
            "rice": "https://images.unsplash.com/photo-1586201375761-83865001e31c?auto=format&fit=crop&w=800&q=80",
            "store_sangel": "https://images.unsplash.com/photo-1578916171728-46686eac8d58?auto=format&fit=crop&w=800&q=80",
            "store_casino": "https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&w=800&q=80",
            "store_ckdo": "https://images.unsplash.com/photo-1604719312566-b76d4685332e?auto=format&fit=crop&w=800&q=80",
            "store_meca": "https://images.unsplash.com/photo-1531297461136-82lw9z1w1w1w?auto=format&fit=crop&w=800&q=80", # broken link intent, fixed below
            "store_meca_real": "https://images.unsplash.com/photo-1597872252165-4827c47d411d?auto=format&fit=crop&w=800&q=80",
            "store_sipagel": "https://images.unsplash.com/photo-1534723452862-4c874018d66d?auto=format&fit=crop&w=800&q=80",
        }
        
        url = image_map.get(query, "https://images.unsplash.com/photo-1550989460-0adf9ea622e2?auto=format&fit=crop&w=800&q=80") # default grocery
        
        response = requests.get(url)
        if response.status_code == 200:
            return ContentFile(response.content)
    except Exception as e:
        print(f"Error downloading image for {query}: {e}")
    return None

def run():
    setup_django()
    from users.models import User
    from stores.models import Store, StoreCategory
    from products.models import Product, ProductCategory
    print("Starting store population script...")
    manager = User.objects.filter(phone='+24100000001', user_type='store_manager').first()
    if not manager:
        print("Manager not found, creating...")
        manager = User.objects.create_user(
            phone='+24100000001',
            password='password123',
            first_name='Jean',
            last_name='Gerant',
            user_type='store_manager'
        )

    # 2. Define Data
    stores_data = [
        {
            "name": "Sangel",
            "category": "Alimentation & Surgelés",
            "description": "Le spécialiste des produits surgelés et de l'alimentation générale.",
            "image_key": "store_sangel",
            "products": [
                {"name": "Cuisse de Poulet 10kg", "price": 12000, "cat": "Surgelés", "image_key": "chicken"},
                {"name": "Poisson Chinchard", "price": 8500, "cat": "Surgelés", "image_key": "fish"},
                {"name": "Riz Parfumé 5kg", "price": 4500, "cat": "Alimentaire", "image_key": "rice"},
            ]
        },
        {
            "name": "Géant Casino Mbolo",
            "category": "Hypermarché",
            "description": "Votre grand centre commercial : Alimentation, Électroménager, Mode.",
            "image_key": "store_casino",
            "products": [
                {"name": "TV Samsung 55 pouces", "price": 350000, "cat": "Électroménager", "image_key": "tv"},
                {"name": "Robe d'été fleurie", "price": 15000, "cat": "Vêtement", "image_key": "shirt"},
                {"name": "Pack Coca Cola 6x1.5L", "price": 4500, "cat": "Boissons", "image_key": "rice"}, # reusing rice img as placeholder or default
            ]
        },
        {
            "name": "Géant CKDO",
            "category": "Hypermarché",
            "description": "Tout ce dont vous avez besoin au meilleur prix.",
            "image_key": "store_ckdo",
            "products": [
                {"name": "Machine à laver LG", "price": 280000, "cat": "Électroménager", "image_key": "washing_machine"},
                {"name": "Sac de Riz 25kg", "price": 18000, "cat": "Alimentaire", "image_key": "rice"},
            ]
        },
        {
            "name": "Gabon Meca",
            "category": "Informatique & High-Tech",
            "description": "Votre partenaire informatique et bureautique.",
            "image_key": "store_meca_real",
            "products": [
                {"name": "Ordinateur Portable HP", "price": 450000, "cat": "Informatique", "image_key": "laptop"},
                {"name": "Souris sans fil Logitech", "price": 12000, "cat": "Accessoires", "image_key": "mouse"},
            ]
        },
        {
            "name": "Sipagel",
            "category": "Alimentation & Surgelés",
            "description": "La qualité surgelée pour tous vos repas.",
            "image_key": "store_sipagel",
            "products": [
                {"name": "Crème Glacée Vanille", "price": 3500, "cat": "Surgelés", "image_key": "ice_cream"},
                {"name": "Mélange de légumes", "price": 2500, "cat": "Surgelés", "image_key": "vegetables"},
            ]
        }
    ]

    for store_info in stores_data:
        print(f"Processing {store_info['name']}...")
        
        # Create/Get Store Category
        cat_obj, _ = StoreCategory.objects.get_or_create(name=store_info['category'])
        
        # Create/Get Store
        store, created = Store.objects.get_or_create(
            name=store_info['name'],
            defaults={
                'manager': manager,
                'category': cat_obj,
                'description': store_info['description'],
                'address': 'Libreville',
                'city': 'Libreville',
                'is_active': True
            }
        )
        
        if created:
            print(f"  Created store {store.name}")
            # Download store image
            img_content = download_image(store_info['image_key'])
            if img_content:
                store.logo.save(f"{store_info['image_key']}.jpg", img_content, save=True)
        else:
            print(f"  Store {store.name} already exists")

        # Create Products
        for prod_info in store_info['products']:
            # Create/Get Product Category
            prod_cat, _ = ProductCategory.objects.get_or_create(
                name=prod_info['cat'],
                store=store
            )
            
            product, p_created = Product.objects.get_or_create(
                name=prod_info['name'],
                store=store,
                defaults={
                    'category': prod_cat,
                    'description': f"Description pour {prod_info['name']}",
                    'price': prod_info['price'],
                    'stock': 50,
                    'is_available': True
                }
            )
            
            if p_created:
                print(f"    Created product {product.name}")
                img_content = download_image(prod_info['image_key'])
                if img_content:
                    product.image.save(f"{prod_info['image_key']}.jpg", img_content, save=True)
            else:
                print(f"    Product {product.name} already exists")

    print("Done!")

if __name__ == "__main__":
    run()
