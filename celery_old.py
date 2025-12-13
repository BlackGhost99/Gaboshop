"""Backup of the original project-level celery entrypoint.

This file was the project's top-level `celery.py` which caused a
shadowing of the installed `celery` package during import time. It has
been renamed to `celery_old.py` to avoid that problem. The active
project Celery application should live in `celery_app.py`.

Kept here as a backup copy for reference.
"""

import sys
import importlib

# Remove the project root from sys.path temporarily so importlib finds the
# installed 'celery' package in site-packages instead of this file.
_project_path = sys.path[0] if sys.path else None
if _project_path is not None:
    try:
        sys.path.pop(0)
    except Exception:
        _project_path = None

try:
    _real = importlib.import_module('celery')
finally:
    if _project_path is not None:
        sys.path.insert(0, _project_path)

# Re-export public names from the real celery package
for _name in dir(_real):
    if not _name.startswith('_'):
        globals()[_name] = getattr(_real, _name)

# Expose the project's Celery app if present (non-fatal)
try:
    from .celery_app import app  # type: ignore
except Exception:
    app = None
