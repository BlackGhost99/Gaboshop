"""
ASGI config for gaboshop project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')

# If channels is installed and routing exists, import channels application root
try:
	from .routing import application as channels_application  # type: ignore
	# Wrap Django ASGI application so both HTTP and WebSocket are handled
	django_asgi_app = get_asgi_application()
	application = channels_application
except Exception:
	# Fallback to default WSGI ASGI app
	application = get_asgi_application()
