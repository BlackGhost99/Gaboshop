"""
URL configuration for gaboshop project.

This file maps the admin and API v1 routes and serves media files
in development (when `DEBUG` is True).
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import HttpResponse
from django.views.generic.base import RedirectView

urlpatterns = [
    path("favicon.ico", RedirectView.as_view(url="/static/favicon.ico", permanent=True)),
    path('', lambda request: HttpResponse(
        "<h1>Gaboshop</h1><p>API running — available endpoints: <a href='/admin/'>admin</a>, "
        "<a href='/api/v1/'>/api/v1/</a></p>",
        content_type='text/html'
    )),
    path('admin/', admin.site.urls),
    path('api/v1/', include('api.v1.urls')),
    path('api/v1/payments/', include('payments.urls')),
    path('api/v1/delivery/', include('delivery.urls')),
]

# Fichiers envoyés (logos, bannières, photos) servis par l'API, depuis la base de
# données ou son disque. Avec Supabase Storage, les images ont leur propre adresse.
if settings.SERVE_MEDIA:
    from django.urls import re_path
    from core.media_views import serve_media
    urlpatterns += [re_path(r'^media/(?P<path>.*)$', serve_media)]
