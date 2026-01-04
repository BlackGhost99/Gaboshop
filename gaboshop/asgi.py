"""
Proxy module for gaboshop.asgi -> Gaboshop.asgi
"""
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_source = _ROOT / 'Gaboshop' / 'asgi.py'

spec = importlib.util.spec_from_file_location('gaboshop.asgi', str(_source))
_top = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_top)

# Re-export application
application = getattr(_top, 'application', None)
