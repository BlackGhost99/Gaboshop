"""Sert les fichiers envoyés : d'abord depuis la base, sinon depuis le disque."""
from django.conf import settings
from django.http import HttpResponse
from django.views.static import serve

# Seules ces images s'affichent dans le navigateur ; tout le reste (HTML, SVG, PDF…) est
# proposé en téléchargement, pour qu'un fichier piégé ne puisse pas exécuter de script.
INLINE_TYPES = {'image/jpeg', 'image/png', 'image/webp', 'image/gif'}


def _harden(response, content_type):
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "default-src 'none'; img-src 'self'; sandbox"
    if content_type not in INLINE_TYPES:
        response['Content-Disposition'] = 'attachment'
    return response


def serve_media(request, path):
    from core.models import StoredFile
    obj = StoredFile.objects.filter(name=path).first()
    if obj is not None:
        content_type = obj.content_type or 'application/octet-stream'
        response = HttpResponse(bytes(obj.content), content_type=content_type)
        response['Cache-Control'] = 'public, max-age=86400'
        return _harden(response, content_type)
    response = serve(request, path, document_root=settings.MEDIA_ROOT)
    return _harden(response, (response.get('Content-Type') or '').split(';')[0])
