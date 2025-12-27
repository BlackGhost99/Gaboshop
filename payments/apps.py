from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'

    def ready(self):
        # Import signals to ensure they're registered when app is ready
        try:
            import payments.signals  # noqa: F401
        except Exception:
            pass
