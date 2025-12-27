from .celery_app import app as celery_app

# Ensure the Celery app is always imported when Django starts
__all__ = ('celery_app',)

