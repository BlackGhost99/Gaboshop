from django.db import migrations


def create_missing_profiles(apps, schema_editor):
    User = apps.get_model('users', 'User')
    LivreurProfile = apps.get_model('users', 'LivreurProfile')
    missing = User.objects.filter(user_type='delivery_agent', livreur_profile__isnull=True)
    LivreurProfile.objects.bulk_create([LivreurProfile(user=user) for user in missing])


class Migration(migrations.Migration):
    dependencies = [('users', '0010_user_singpay_disbursement_id')]
    operations = [migrations.RunPython(create_missing_profiles, migrations.RunPython.noop)]
