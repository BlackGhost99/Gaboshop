"""
URL configuration for gaboshop project.

This file maps the admin and API v1 routes and serves media files
in development (when `DEBUG` is True).
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

urlpatterns = [
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

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
