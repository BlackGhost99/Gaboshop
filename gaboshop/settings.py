"""
Proxy module for gaboshop.settings -> settings (root level)
This bypasses Gaboshop/settings.py to avoid circular imports.
"""
import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_source = _ROOT / 'settings.py'  # Import directly from root, not from Gaboshop/

spec = importlib.util.spec_from_file_location('gaboshop.settings', str(_source))
_top = importlib.util.module_from_spec(spec)
spec.loader.exec_module(_top)

# Re-export all attributes
for name, val in vars(_top).items():
    globals()[name] = val
