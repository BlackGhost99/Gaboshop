#!/bin/sh
set -e

# Diagnostic sans secret : montre ce que Django utilise pour se connecter a la base
python - <<'PY'
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
from django.conf import settings
d = settings.DATABASES["default"]
print("DB ->", d["ENGINE"].split(".")[-1], "user=%r host=%r port=%r name=%r password_length=%d" % (d.get("USER"), d.get("HOST"), d.get("PORT"), d.get("NAME"), len(d.get("PASSWORD") or "")), flush=True)
PY

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec gunicorn wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers "${GUNICORN_WORKERS:-3}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-60}"
