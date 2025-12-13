"""
Proxy module for project settings so `import gaboshop.settings` works while
keeping the existing top-level settings.py file.
"""
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_source = _ROOT / 'settings.py'

spec = importlib.util.spec_from_file_location('top_settings', str(_source))
_top = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_top)

# Re-export relevant attributes (all UPPERCASE and common names)
for name, val in vars(_top).items():
    if name.isupper() or name in ('BASE_DIR', 'INSTALLED_APPS', 'MIDDLEWARE'):
        globals()[name] = val

# also keep module reference for introspection
_top_settings = _top
