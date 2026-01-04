"""
Proxy module for gaboshop.urls -> urls (root level)
This bypasses Gaboshop/urls.py to avoid circular imports.
"""
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_source = _ROOT / 'urls.py'  # Import directly from root, not from Gaboshop/

spec = importlib.util.spec_from_file_location('gaboshop.urls', str(_source))
_top = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_top)

# Re-export urlpatterns
urlpatterns = getattr(_top, 'urlpatterns', [])
