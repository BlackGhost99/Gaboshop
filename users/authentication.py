from rest_framework import authentication, exceptions
from django.utils.translation import gettext_lazy as _
from .models import DeliveryAgentApiKey
from django.utils import timezone


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """Authenticate users using an API key.

    Supported formats:
    - Authorization: ApiKey <key>
    - Authorization: ApiKey=<key>
    - X-Api-Key: <key>

    This authenticator is intended for delivery agents (mobile clients).
    """

    keyword = 'ApiKey'

    def authenticate(self, request):
        # Try Authorization header first (robust parsing)
        auth_header = authentication.get_authorization_header(request)
        key = None

        if auth_header:
            try:
                header = auth_header.decode()
            except UnicodeError:
                raise exceptions.AuthenticationFailed(_('Invalid ApiKey header.'))

            low = header.lower()
            if low.startswith(self.keyword.lower() + ' '):
                key = header.split(None, 1)[1].strip()
            elif low.startswith(self.keyword.lower() + '='):
                key = header.split('=', 1)[1].strip()

        # Fallback to X-Api-Key header (many mobile clients prefer custom header)
        if not key:
            # Django normalizes headers to HTTP_<NAME>
            key = request.META.get('HTTP_X_API_KEY') or request.META.get('HTTP_X-API-KEY') or request.META.get('HTTP_X_APIKEY')
            # request.headers is available on newer Django versions
            if not key and hasattr(request, 'headers'):
                key = request.headers.get('X-Api-Key')

        if not key:
            return None

        try:
            api = DeliveryAgentApiKey.objects.select_related('user').get(key=key)
        except DeliveryAgentApiKey.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid API key.'))

        user = api.user
        if not getattr(user, 'is_delivery_agent', lambda: False)():
            raise exceptions.AuthenticationFailed(_('User is not a delivery agent.'))

        try:
            api.last_used_at = timezone.now()
            api.save(update_fields=['last_used_at'])
        except Exception:
            pass

        return (user, None)
