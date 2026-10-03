from decimal import Decimal

from django.db import migrations


def apply_vehicle_bounds(apps, schema_editor):
    VehicleType = apps.get_model('delivery', 'VehicleType')
    updates = {
        'MOTO': {
            'max_weight_kg': Decimal('30.00'),
            'max_length_m': Decimal('0.50'),
            'allow_intercity': False,
        },
        'CAR': {
            'max_weight_kg': Decimal('80.00'),
            'max_length_m': Decimal('1.00'),
            'allow_intercity': True,
        },
        'VAN': {
            'max_weight_kg': Decimal('150.00'),
            'max_length_m': Decimal('2.00'),
            'allow_intercity': True,
        },
        'TRUCK': {
            'max_weight_kg': Decimal('9999.00'),
            'max_length_m': Decimal('5.00'),
            'allow_intercity': True,
        },
    }
    for name, fields in updates.items():
        VehicleType.objects.filter(name=name).update(**fields)


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0010_vehicletype_max_length_m'),
    ]

    operations = [
        migrations.RunPython(apply_vehicle_bounds, migrations.RunPython.noop),
    ]
