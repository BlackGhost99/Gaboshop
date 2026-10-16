"""Clés VAPID : elles prouvent aux services d'alertes des navigateurs que l'alerte vient bien de ce site.

Si VAPID_PUBLIC_KEY et VAPID_PRIVATE_KEY sont dans l'environnement, elles passent en premier. Sinon le site crée
sa propre paire au premier besoin et la garde en base : personne n'a rien à saisir, et le site de test et le vrai
site ont chacun la leur (une alerte de l'un ne peut pas partir de l'autre).
"""
import base64
import logging

from django.conf import settings

logger = logging.getLogger(__name__)
_cache = {}


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


def generate_pair():
    """(clé publique, clé privée) au format attendu par les navigateurs et par pywebpush (base64 sans remplissage)."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    private = ec.generate_private_key(ec.SECP256R1())
    private_raw = private.private_numbers().private_value.to_bytes(32, 'big')
    public_raw = private.public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint,
    )
    return _b64(public_raw), _b64(private_raw)


def get_keys():
    """(public, private) ou (None, None) si l'envoi d'alertes est coupé (PUSH_ENABLED = False)."""
    if not getattr(settings, 'PUSH_ENABLED', True):
        return None, None
    public = getattr(settings, 'VAPID_PUBLIC_KEY', '') or ''
    private = getattr(settings, 'VAPID_PRIVATE_KEY', '') or ''
    if public and private:
        return public, private
    if _cache.get('pair'):
        return _cache['pair']
    from .models import PushKeyPair
    pair = PushKeyPair.objects.filter(pk=1).first()
    if pair is None:
        public, private = generate_pair()
        # Ligne unique (pk=1) : deux processus qui démarrent ensemble gardent la même paire.
        pair, created = PushKeyPair.objects.get_or_create(pk=1, defaults={'public_key': public, 'private_key': private})
        if created:
            logger.info('Clés VAPID créées pour ce site.')
    _cache['pair'] = (pair.public_key, pair.private_key)
    return _cache['pair']


def clear_cache():
    _cache.clear()


def subject():
    return getattr(settings, 'VAPID_SUBJECT', '') or 'mailto:contact@gaboshop.ga'
