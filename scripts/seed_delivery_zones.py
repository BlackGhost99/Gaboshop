"""
Seed script to pre-populate delivery zones and vehicle rates for Gabon.
Creates zones for major cities (Libreville, Owendo, Akanda, Port-Gentil)
and configures pricing for bike, motorbike, and van.
"""

import os
import django
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gaboshop.settings')
django.setup()

from delivery.models import DeliveryZone, VehicleType, ZoneVehicleRate


def seed_zones_and_rates():
    """
    Create delivery zones and their vehicle rate configurations.
    """
    
    print("🔄 Starting delivery zones seed...")
    
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
            print(f"✅ Created zone: {zone.name} ({zone.city})")
        else:
            print(f"⏭️  Zone already exists: {zone.name} ({zone.city})")
        
        key = f"{zone.city}_{zone.name}"
        created_zones[key] = zone
    
    # Get or create vehicle types
    print("\n🚗 Configuring vehicle types...")
    
    bike, _ = VehicleType.objects.get_or_create(
        name='BIKE',
        defaults={
            'max_weight_kg': Decimal('5.00'),
            'max_items': 10,
            'max_distance_km': Decimal('10.00'),
            'allow_intercity': False,
            'base_price_intra_city': Decimal('2000.00'),
            'price_per_km_intra_city': Decimal('200.00'),
            'base_price_inter_city': Decimal('3000.00'),
            'price_per_km_inter_city': Decimal('300.00'),
            'is_active': True,
        }
    )
    print(f"✅ Bike vehicle type ready: {bike.get_name_display()}")
    
    motorbike, _ = VehicleType.objects.get_or_create(
        name='MOTO',
        defaults={
            'max_weight_kg': Decimal('20.00'),
            'max_items': 30,
            'max_distance_km': Decimal('50.00'),
            'allow_intercity': True,
            'base_price_intra_city': Decimal('3500.00'),
            'price_per_km_intra_city': Decimal('250.00'),
            'base_price_inter_city': Decimal('5000.00'),
            'price_per_km_inter_city': Decimal('400.00'),
            'is_active': True,
        }
    )
    print(f"✅ Motorbike vehicle type ready: {motorbike.get_name_display()}")
    
    van, _ = VehicleType.objects.get_or_create(
        name='VAN',
        defaults={
            'max_weight_kg': Decimal('100.00'),
            'max_items': 999,
            'max_distance_km': Decimal('200.00'),
            'allow_intercity': True,
            'base_price_intra_city': Decimal('5000.00'),
            'price_per_km_intra_city': Decimal('300.00'),
            'base_price_inter_city': Decimal('8000.00'),
            'price_per_km_inter_city': Decimal('500.00'),
            'is_active': True,
        }
    )
    print(f"✅ Van vehicle type ready: {van.get_name_display()}")
    
    # Define zone-specific vehicle rates
    # Adjust pricing based on zone demand and distance
    rates_config = [
        # Libreville Centre-Ville (high demand, short distance)
        {'zone_key': 'Libreville_Centre-Ville', 'vehicles': [
            {'vehicle': bike, 'base_price': Decimal('2000.00'), 'price_per_km': Decimal('150.00')},
            {'vehicle': motorbike, 'base_price': Decimal('3000.00'), 'price_per_km': Decimal('200.00')},
            {'vehicle': van, 'base_price': Decimal('4500.00'), 'price_per_km': Decimal('250.00')},
        ]},
        # Libreville Louis
        {'zone_key': 'Libreville_Louis', 'vehicles': [
            {'vehicle': bike, 'base_price': Decimal('2500.00'), 'price_per_km': Decimal('175.00')},
            {'vehicle': motorbike, 'base_price': Decimal('3500.00'), 'price_per_km': Decimal('225.00')},
            {'vehicle': van, 'base_price': Decimal('5000.00'), 'price_per_km': Decimal('275.00')},
        ]},
        # Libreville Mont-Bouët
        {'zone_key': 'Libreville_Mont-Bouët', 'vehicles': [
            {'vehicle': bike, 'base_price': Decimal('3000.00'), 'price_per_km': Decimal('200.00')},
            {'vehicle': motorbike, 'base_price': Decimal('4000.00'), 'price_per_km': Decimal('250.00')},
            {'vehicle': van, 'base_price': Decimal('5500.00'), 'price_per_km': Decimal('300.00')},
        ]},
        # Owendo Centre Commercial (port area, bulk delivery)
        {'zone_key': 'Owendo_Centre Commercial', 'vehicles': [
            {'vehicle': motorbike, 'base_price': Decimal('4500.00'), 'price_per_km': Decimal('300.00')},
            {'vehicle': van, 'base_price': Decimal('6500.00'), 'price_per_km': Decimal('350.00')},
        ]},
        # Owendo Résidentiel
        {'zone_key': 'Owendo_Résidentiel', 'vehicles': [
            {'vehicle': motorbike, 'base_price': Decimal('5000.00'), 'price_per_km': Decimal('350.00')},
            {'vehicle': van, 'base_price': Decimal('7000.00'), 'price_per_km': Decimal('400.00')},
        ]},
        # Akanda Centre-Ville
        {'zone_key': 'Akanda_Centre-Ville', 'vehicles': [
            {'vehicle': motorbike, 'base_price': Decimal('4000.00'), 'price_per_km': Decimal('250.00')},
            {'vehicle': van, 'base_price': Decimal('6000.00'), 'price_per_km': Decimal('300.00')},
        ]},
        # Port-Gentil Centre (inter-city)
        {'zone_key': 'Port-Gentil_Centre', 'vehicles': [
            {'vehicle': motorbike, 'base_price': Decimal('7000.00'), 'price_per_km': Decimal('500.00')},
            {'vehicle': van, 'base_price': Decimal('10000.00'), 'price_per_km': Decimal('600.00')},
        ]},
    ]
    
    # Create zone-vehicle rates
    print("\n💰 Configuring zone-vehicle rates...")
    
    for rate_config in rates_config:
        zone_key = rate_config['zone_key']
        zone = created_zones.get(zone_key)
        
        if not zone:
            print(f"⚠️  Zone not found: {zone_key}, skipping...")
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
                print(f"✅ Created rate: {zone.name} + {vehicle.get_name_display()} = {base_price} + {price_per_km}/km")
            else:
                print(f"⏭️  Rate already exists: {zone.name} + {vehicle.get_name_display()}")
    
    print("\n✨ Seed complete! Delivery zones and rates are now configured.")
    print(f"📊 Summary:")
    print(f"   - {DeliveryZone.objects.filter(is_active=True).count()} active zones")
    print(f"   - {VehicleType.objects.filter(is_active=True).count()} active vehicle types")
    print(f"   - {ZoneVehicleRate.objects.filter(is_active=True).count()} active rate configurations")


if __name__ == '__main__':
    seed_zones_and_rates()
