"""Sert les fichiers envoyés : d'abord depuis la base, sinon depuis le disque."""
from django.conf import settings
from django.http import HttpResponse
from django.views.static import serve


def serve_media(request, path):
    from core.models import StoredFile
    obj = StoredFile.objects.filter(name=path).first()
    if obj is not None:
        response = HttpResponse(bytes(obj.content), content_type=obj.content_type or 'application/octet-stream')
        response['Cache-Control'] = 'public, max-age=86400'
        return response
    return serve(request, path, document_root=settings.MEDIA_ROOT)
