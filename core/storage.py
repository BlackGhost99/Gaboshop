"""
Stockage des fichiers envoyés dans la base de données (modèle StoredFile).

Les images trop lourdes sont réduites (1600 px max) pour ménager la base.
Les fichiers sont servis par core.media_views.serve_media sous MEDIA_URL.
"""
import io
import mimetypes

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible

MAX_IMAGE_SIDE = 1600
SHRINK_ABOVE_BYTES = 400 * 1024


def _shrink_image(data, name):
    """Réduit une image lourde ; renvoie les octets d'origine si ce n'en est pas une."""
    if len(data) <= SHRINK_ABOVE_BYTES:
        return data
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(data))
        fmt = (img.format or '').upper()
        if fmt not in ('JPEG', 'PNG', 'WEBP'):
            return data
        img = ImageOps.exif_transpose(img)
        img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        out = io.BytesIO()
        if fmt == 'JPEG':
            img.convert('RGB').save(out, 'JPEG', quality=82, optimize=True)
        elif fmt == 'WEBP':
            img.save(out, 'WEBP', quality=82)
        else:
            img.save(out, 'PNG', optimize=True)
        result = out.getvalue()
        return result if len(result) < len(data) else data
    except Exception:
        return data


@deconstructible
class DatabaseStorage(Storage):
    def _model(self):
        from core.models import StoredFile
        return StoredFile

    def _open(self, name, mode='rb'):
        obj = self._model().objects.get(name=name)
        return ContentFile(bytes(obj.content), name=name)

    def _save(self, name, content):
        if hasattr(content, 'seek'):
            content.seek(0)
        data = content.read()
        if isinstance(data, str):
            data = data.encode()
        data = _shrink_image(data, name)
        content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        self._model().objects.update_or_create(
            name=name,
            defaults={'content': data, 'content_type': content_type, 'size': len(data)},
        )
        return name

    def exists(self, name):
        return self._model().objects.filter(name=name).exists()

    def delete(self, name):
        self._model().objects.filter(name=name).delete()

    def size(self, name):
        obj = self._model().objects.filter(name=name).only('size').first()
        return obj.size if obj else 0

    def url(self, name):
        return f"{settings.MEDIA_URL}{name}"
