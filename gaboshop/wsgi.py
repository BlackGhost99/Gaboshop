"""
Proxy WSGI module that re-exports application from top-level wsgi.py
"""
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_source = _ROOT / 'wsgi.py'

spec = importlib.util.spec_from_file_location('top_wsgi', str(_source))
_top = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_top)

application = getattr(_top, 'application')
