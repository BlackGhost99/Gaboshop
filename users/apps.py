from django.apps import AppConfig


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Gestion des Utilisateurs'
    
    def ready(self):
        # Import des signaux si nécessaire
        try:
            import users.signals  # noqa: F401
        except Exception:
            # signals module is optional; fail silently if not present
            pass
