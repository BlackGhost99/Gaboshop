#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# Force PYTHONPATH to include the project root
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Force registration of gaboshop package before Django is loaded
# This allows 'import gaboshop' to work even though directory is 'Gaboshop'
# On Windows, filesystem is case-insensitive but Python imports are case-sensitive
try:
    import types
    
    # Register gaboshop package (note: directory is 'Gaboshop' but we import as 'gaboshop')
    gaboshop_dir = BASE_DIR / 'Gaboshop'
    gaboshop_init = gaboshop_dir / '__init__.py'
    
    if gaboshop_init.exists():
        # Create and register the parent gaboshop module
        gaboshop_module = types.ModuleType('gaboshop')
        gaboshop_module.__path__ = [str(gaboshop_dir)]
        gaboshop_module.__file__ = str(gaboshop_init)
        gaboshop_module.__package__ = ''
        sys.modules['gaboshop'] = gaboshop_module
except Exception:
    # If registration fails, Django will try to import it normally
    pass


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
