"""
Seed script to pre-populate delivery zones and vehicle rates for Gabon.
Creates zones for major cities (Libreville, Owendo, Akanda, Port-Gentil)
and configures pricing for moto, car, van, and truck.
"""

import os
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gaboshop.settings')
django.setup()

from delivery.models import DeliveryZone, VehicleType, ZoneVehicleRate


def ensure_vehicle_defaults(vehicle, defaults):
    updated = False
    for field, value in defaults.items():
        if getattr(vehicle, field) != value:
            setattr(vehicle, field, value)
            updated = True
    if updated:
        vehicle.save()


def seed_zones_and_rates():
    """
    Create delivery zones and their vehicle rate configurations.
    """
    
    print("?? Starting delivery zones seed...")
    
    # Define zones
    zones_data = [
        {
            'name': 'Centre-Ville',
            'city': 'Libreville',
            'description': 'Zone Centre-Ville de Libreville (Boulevard de la Mer, commerce, administratif)',
            'inter_city_surcharge': Decimal('1500.00'),
        },
        {
            'name': 'Louis',
            'city': 'Libreville',
            'description': 'Quartier Louis, zone résidentielle proche du centre',
            'inter_city_surcharge': Decimal('2000.00'),
        },
        {
            'name': 'Mont-Bouët',
            'city': 'Libreville',
            'description': 'Quartier Mont-Bouët, zone de commerce et habitation',
            'inter_city_surcharge': Decimal('2500.00'),
        },
        {
            'name': 'Centre Commercial',
            'city': 'Owendo',
            'description': 'Zone commerciale de Owendo (port, commerce de gros)',
            'inter_city_surcharge': Decimal('3000.00'),
        },
        {
            'name': 'Résidentiel',
            'city': 'Owendo',
            'description': 'Zones résidentielles de Owendo',
            'inter_city_surcharge': Decimal('3500.00'),
        },
        {
            'name': 'Centre-Ville',
            'city': 'Akanda',
            'description': 'Centre-Ville d\'Akanda, zone de développement',
            'inter_city_surcharge': Decimal('2500.00'),
        },
        {
            'name': 'Centre',
            'city': 'Port-Gentil',
            'description': 'Centre de Port-Gentil, zone côtière',
            'inter_city_surcharge': Decimal('4000.00'),
        },
    ]
    
    # Create zones
    created_zones = {}
    for zone_data in zones_data:
        zone, created = DeliveryZone.objects.get_or_create(
            name=zone_data['name'],
            city=zone_data['city'],
            defaults={
                'description': zone_data['description'],
                'inter_city_surcharge': zone_data['inter_city_surcharge'],
                'is_active': True,
            }
        )
        
        if created:
            print(f"? Created zone: {zone.name} ({zone.city})")
        else:
            print(f"??  Zone already exists: {zone.name} ({zone.city})")
        
        key = f"{zone.city}_{zone.name}"
        created_zones[key] = zone
    
    # Get or create vehicle types
    print("\n?? Configuring vehicle types...")
    
    moto_defaults = {
            'max_weight_kg': Decimal('30.00'),
            'max_length_m': Decimal('0.50'),
            'max_items': 30,
            'max_distance_km': Decimal('50.00'),
            'allow_intercity': False,
            'base_price_intra_city': Decimal('3000.00'),
            'price_per_km_intra_city': Decimal('200.00'),
            'base_price_inter_city': Decimal('4500.00'),
            'price_per_km_inter_city': Decimal('300.00'),
            'is_active': True,
        }
    moto, _ = VehicleType.objects.get_or_create(
        name='MOTO',
        defaults=moto_defaults
    )
    ensure_vehicle_defaults(moto, moto_defaults)
    print(f"? Moto vehicle type ready: {moto.get_name_display()}")
    
    car_defaults = {
            'max_weight_kg': Decimal('80.00'),
            'max_length_m': Decimal('1.00'),
            'max_items': 60,
            'max_distance_km': Decimal('120.00'),
            'allow_intercity': True,
            'base_price_intra_city': Decimal('4000.00'),
            'price_per_km_intra_city': Decimal('250.00'),
            'base_price_inter_city': Decimal('6000.00'),
            'price_per_km_inter_city': Decimal('400.00'),
            'is_active': True,
        }
    car, _ = VehicleType.objects.get_or_create(
        name='CAR',
        defaults=car_defaults
    )
    ensure_vehicle_defaults(car, car_defaults)
    print(f"? Car vehicle type ready: {car.get_name_display()}")
    
    van_defaults = {
            'max_weight_kg': Decimal('150.00'),
            'max_length_m': Decimal('2.00'),
            'max_items': 120,
            'max_distance_km': Decimal('200.00'),
            'allow_intercity': True,
            'base_price_intra_city': Decimal('6000.00'),
            'price_per_km_intra_city': Decimal('300.00'),
            'base_price_inter_city': Decimal('9000.00'),
            'price_per_km_inter_city': Decimal('500.00'),
            'is_active': True,
        }
    van, _ = VehicleType.objects.get_or_create(
        name='VAN',
        defaults=van_defaults
    )
    ensure_vehicle_defaults(van, van_defaults)
    print(f"? Van vehicle type ready: {van.get_name_display()}")
    
    truck_defaults = {
            'max_weight_kg': Decimal('9999.00'),
            'max_length_m': Decimal('5.00'),
            'max_items': 300,
            'max_distance_km': Decimal('400.00'),
            'allow_intercity': True,
            'base_price_intra_city': Decimal('9000.00'),
            'price_per_km_intra_city': Decimal('450.00'),
            'base_price_inter_city': Decimal('12000.00'),
            'price_per_km_inter_city': Decimal('700.00'),
            'is_active': True,
        }
    truck, _ = VehicleType.objects.get_or_create(
        name='TRUCK',
        defaults=truck_defaults
    )
    ensure_vehicle_defaults(truck, truck_defaults)
    print(f"? Truck vehicle type ready: {truck.get_name_display()}")
    
    # Define zone-specific vehicle rates
    # Adjust pricing based on zone demand and distance
    rates_config = [
        # Libreville Centre-Ville (high demand, short distance)
        {'zone_key': 'Libreville_Centre-Ville', 'vehicles': [
            {'vehicle': moto, 'base_price': Decimal('3000.00'), 'price_per_km': Decimal('200.00')},
            {'vehicle': car, 'base_price': Decimal('3800.00'), 'price_per_km': Decimal('225.00')},
            {'vehicle': van, 'base_price': Decimal('4500.00'), 'price_per_km': Decimal('250.00')},
            {'vehicle': truck, 'base_price': Decimal('7000.00'), 'price_per_km': Decimal('350.00')},
        ]},
        # Libreville Louis
        {'zone_key': 'Libreville_Louis', 'vehicles': [
            {'vehicle': moto, 'base_price': Decimal('3500.00'), 'price_per_km': Decimal('225.00')},
            {'vehicle': car, 'base_price': Decimal('4250.00'), 'price_per_km': Decimal('250.00')},
            {'vehicle': van, 'base_price': Decimal('5000.00'), 'price_per_km': Decimal('275.00')},
            {'vehicle': truck, 'base_price': Decimal('7500.00'), 'price_per_km': Decimal('375.00')},
        ]},
        # Libreville Mont-Bouët
        {'zone_key': 'Libreville_Mont-Bouët', 'vehicles': [
            {'vehicle': moto, 'base_price': Decimal('4000.00'), 'price_per_km': Decimal('250.00')},
            {'vehicle': car, 'base_price': Decimal('4750.00'), 'price_per_km': Decimal('275.00')},
            {'vehicle': van, 'base_price': Decimal('5500.00'), 'price_per_km': Decimal('300.00')},
            {'vehicle': truck, 'base_price': Decimal('8000.00'), 'price_per_km': Decimal('400.00')},
        ]},
        # Owendo Centre Commercial (port area, bulk delivery)
        {'zone_key': 'Owendo_Centre Commercial', 'vehicles': [
            {'vehicle': moto, 'base_price': Decimal('4500.00'), 'price_per_km': Decimal('300.00')},
            {'vehicle': car, 'base_price': Decimal('5500.00'), 'price_per_km': Decimal('325.00')},
            {'vehicle': van, 'base_price': Decimal('6500.00'), 'price_per_km': Decimal('350.00')},
            {'vehicle': truck, 'base_price': Decimal('9000.00'), 'price_per_km': Decimal('450.00')},
        ]},
        # Owendo Résidentiel
        {'zone_key': 'Owendo_Résidentiel', 'vehicles': [
            {'vehicle': moto, 'base_price': Decimal('5000.00'), 'price_per_km': Decimal('350.00')},
            {'vehicle': car, 'base_price': Decimal('6000.00'), 'price_per_km': Decimal('375.00')},
            {'vehicle': van, 'base_price': Decimal('7000.00'), 'price_per_km': Decimal('400.00')},
            {'vehicle': truck, 'base_price': Decimal('9500.00'), 'price_per_km': Decimal('500.00')},
        ]},
        # Akanda Centre-Ville
        {'zone_key': 'Akanda_Centre-Ville', 'vehicles': [
            {'vehicle': moto, 'base_price': Decimal('4000.00'), 'price_per_km': Decimal('250.00')},
            {'vehicle': car, 'base_price': Decimal('5000.00'), 'price_per_km': Decimal('275.00')},
            {'vehicle': van, 'base_price': Decimal('6000.00'), 'price_per_km': Decimal('300.00')},
            {'vehicle': truck, 'base_price': Decimal('8500.00'), 'price_per_km': Decimal('400.00')},
        ]},
        # Port-Gentil Centre (inter-city)
        {'zone_key': 'Port-Gentil_Centre', 'vehicles': [
            {'vehicle': moto, 'base_price': Decimal('7000.00'), 'price_per_km': Decimal('500.00')},
            {'vehicle': car, 'base_price': Decimal('8500.00'), 'price_per_km': Decimal('550.00')},
            {'vehicle': van, 'base_price': Decimal('10000.00'), 'price_per_km': Decimal('600.00')},
            {'vehicle': truck, 'base_price': Decimal('14000.00'), 'price_per_km': Decimal('800.00')},
        ]},
    ]
    
    # Create zone-vehicle rates
    print("\n?? Configuring zone-vehicle rates...")
    
    for rate_config in rates_config:
        zone_key = rate_config['zone_key']
        zone = created_zones.get(zone_key)
        
        if not zone:
            print(f"??  Zone not found: {zone_key}, skipping...")
            continue
        
        for vehicle_rate in rate_config['vehicles']:
            vehicle = vehicle_rate['vehicle']
            base_price = vehicle_rate['base_price']
            price_per_km = vehicle_rate['price_per_km']
            
            rate, created = ZoneVehicleRate.objects.get_or_create(
                zone=zone,
                vehicle=vehicle,
                defaults={
                    'base_price': base_price,
                    'price_per_km': price_per_km,
                    'is_active': True,
                    'notes': f"Tarif configuré pour {zone.name} ({zone.city}) - {vehicle.get_name_display()}",
                }
            )
            
            if created:
                print(f"? Created rate: {zone.name} + {vehicle.get_name_display()} = {base_price} + {price_per_km}/km")
            else:
                print(f"??  Rate already exists: {zone.name} + {vehicle.get_name_display()}")
    
    print("\n? Seed complete! Delivery zones and rates are now configured.")
    print(f"?? Summary:")
    print(f"   - {DeliveryZone.objects.filter(is_active=True).count()} active zones")
    print(f"   - {VehicleType.objects.filter(is_active=True).count()} active vehicle types")
    print(f"   - {ZoneVehicleRate.objects.filter(is_active=True).count()} active rate configurations")


if __name__ == '__main__':
    seed_zones_and_rates()
