"""
Proxy for top-level urls.py so `import gaboshop.urls` resolves.
"""
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_source = _ROOT / 'urls.py'

spec = importlib.util.spec_from_file_location('top_urls', str(_source))
_top = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_top)

# expose urlpatterns if present
urlpatterns = getattr(_top, 'urlpatterns', [])
