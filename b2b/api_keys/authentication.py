"""Authentification par clé d'intégration (grossistes) et limitation de débit.

La clé s'envoie dans ``Authorization: Api-Key <clé>`` ou dans ``X-API-Key``. Elle ne marche que si :
- elle est active (non révoquée) ;
- le commerce est un grossiste actif ;
- son forfait inclut encore l'option « Accès API » (sinon la clé est coupée, sans être supprimée : elle
  repart dès que le forfait redevient valable).
"""
from rest_framework import authentication, exceptions, permissions
from rest_framework.throttling import SimpleRateThrottle

from b2b.models import WholesalerApiKey
from b2b.models.api_key import hash_api_key
from payments.plan_features import has, required_message

KEYWORD = 'Api-Key'
HOW_TO_SEND = "Envoyez votre clé dans l'en-tête « Authorization: Api-Key <votre clé> » (ou « X-API-Key »)."
PLAN_LOST = "L'accès API n'est plus inclus dans votre forfait."


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """Renvoie (gérant du grossiste, clé) : la clé (``request.auth``) fixe le grossiste, jamais l'utilisateur."""

    def authenticate_header(self, request):
        return f'{KEYWORD} realm="Gaboshop"'

    @staticmethod
    def _read_key(request):
        parts = authentication.get_authorization_header(request).split()
        if parts and parts[0].lower() == KEYWORD.lower().encode():
            if len(parts) != 2:
                raise exceptions.AuthenticationFailed(f"En-tête Authorization mal formé. {HOW_TO_SEND}")
            try:
                return parts[1].decode()
            except UnicodeError:
                raise exceptions.AuthenticationFailed("Clé API invalide ou révoquée.")
        return (request.META.get('HTTP_X_API_KEY') or '').strip()

    def authenticate(self, request):
        raw = self._read_key(request)
        if not raw:
            raise exceptions.AuthenticationFailed(f"Clé API manquante. {HOW_TO_SEND}")
        key = (WholesalerApiKey.objects.select_related('store', 'store__manager')
               .filter(key_hash=hash_api_key(raw), is_active=True).first())
        if key is None:
            raise exceptions.AuthenticationFailed("Clé API invalide ou révoquée. Créez-en une nouvelle dans « Accès API ».")
        store = key.store
        if not store.is_active or not store.is_b2b or not store.manager.is_active:
            raise exceptions.PermissionDenied("Ce compte grossiste n'est pas actif : la clé est suspendue.")
        plan = store.get_current_plan()
        if not has(plan, 'api_access'):
            raise exceptions.PermissionDenied(f"{PLAN_LOST} {required_message('api_access', plan)}")
        key.touch()
        return store.manager, key


class HasWholesalerApiKey(permissions.BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, WholesalerApiKey)


class ApiKeyRateThrottle(SimpleRateThrottle):
    """60 requêtes par minute et par clé (la clé, pas l'adresse : un logiciel hébergé partage la sienne)."""
    scope = 'wholesaler_api_key'
    rate = '60/minute'

    def get_cache_key(self, request, view):
        if not isinstance(request.auth, WholesalerApiKey):
            return None
        return self.cache_format % {'scope': self.scope, 'ident': request.auth.pk}
