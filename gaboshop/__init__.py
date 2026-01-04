"""
Proxy package for gaboshop -> Gaboshop compatibility.
This allows 'import gaboshop' to work even though the directory is named 'Gaboshop'.
"""
import sys
from pathlib import Path

# Get the parent directory
_PARENT = Path(__file__).resolve().parent.parent
_GABOSHOP_DIR = _PARENT / 'Gaboshop'

# Make sure parent is in sys.path
if str(_PARENT) not in sys.path:
    sys.path.insert(0, str(_PARENT))

# Register this module as 'gaboshop' (lowercase) in sys.modules
# This allows imports like 'from gaboshop import settings' to work
# Note: This file is in the 'Gaboshop' directory, but we register it as 'gaboshop'
if 'gaboshop' not in sys.modules:
    # Register the current module (which is actually 'Gaboshop') as 'gaboshop'
    sys.modules['gaboshop'] = sys.modules.get(__name__, sys.modules.get('Gaboshop'))