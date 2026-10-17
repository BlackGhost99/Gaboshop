"""Clés d'intégration des grossistes (option « Accès API » du forfait).

Une clé complète n'existe qu'au moment de sa création : elle est montrée une seule fois au grossiste.
La base ne garde que son empreinte SHA-256 et un préfixe de 8 caractères pour la reconnaître dans la liste.
"""
import hashlib
import secrets

from django.db import models
from django.utils import timezone

KEY_PREFIX_LENGTH = 8
KEY_MARK = 'gbw_'
MAX_ACTIVE_KEYS = 5


def hash_api_key(raw_key):
    return hashlib.sha256((raw_key or '').encode('utf-8')).hexdigest()


class WholesalerApiKey(models.Model):
    store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='api_keys')
    name = models.CharField(max_length=80, help_text="Nom donné par le grossiste (ex. « Logiciel de caisse »)")
    prefix = models.CharField(max_length=KEY_PREFIX_LENGTH, help_text="Début de la clé, visible dans la liste")
    key_hash = models.CharField(max_length=64, unique=True, editable=False, help_text="Empreinte SHA-256 de la clé")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Clé API grossiste"
        verbose_name_plural = "Clés API grossistes"
        ordering = ['-created_at']
        indexes = [models.Index(fields=['store', 'is_active'], name='b2b_apikey_store_active_idx')]

    def __str__(self):
        return f"{self.name} ({self.prefix}…) - {self.store.name}"

    @classmethod
    def generate(cls, store, name):
        """Crée une clé et renvoie (clé enregistrée, clé complète). La clé complète n'est stockée nulle part."""
        raw = KEY_MARK + secrets.token_urlsafe(32)
        key = cls.objects.create(store=store, name=name, prefix=raw[:KEY_PREFIX_LENGTH], key_hash=hash_api_key(raw))
        return key, raw

    def revoke(self):
        if self.is_active:
            self.is_active = False
            self.revoked_at = timezone.now()
            self.save(update_fields=['is_active', 'revoked_at'])

    def touch(self, every_seconds=60):
        """Note la dernière utilisation, au plus une écriture par minute (la clé peut servir 60 fois par minute)."""
        now = timezone.now()
        if self.last_used_at is None or (now - self.last_used_at).total_seconds() >= every_seconds:
            self.last_used_at = now
            type(self).objects.filter(pk=self.pk).update(last_used_at=now)
