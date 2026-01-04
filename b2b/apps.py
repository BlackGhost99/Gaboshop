"""
Configuration de l'application B2B
"""
from django.apps import AppConfig


class B2BConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'b2b'
    verbose_name = 'B2B (Business to Business)'

