from django.core.management.base import BaseCommand
from api.models import SystemSettings


class Command(BaseCommand):
    help = 'Initialise les paramètres système avec les valeurs par défaut'

    def handle(self, *args, **kwargs):
        settings = SystemSettings.get_settings()
        
        if settings:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Paramètres système initialisés avec succès!\n'
                    f'   Commission globale: {settings.commission_global}%\n'
                    f'   Ville par défaut: {settings.default_city}\n'
                    f'   Prix par km: {settings.price_per_km} FCFA\n'
                    f'   Paiement avant commande: {"Oui" if settings.payment_before_order else "Non"}\n'
                    f'\n'
                    f'👉 Accédez au Django Admin pour modifier ces paramètres:\n'
                    f'   http://localhost:8000/admin/api/systemsettings/\n'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR('❌ Erreur lors de l\'initialisation des paramètres système')
            )
