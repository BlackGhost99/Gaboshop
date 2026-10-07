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

# Ne pas arreter le conteneur en silence : afficher le code de sortie (137 = manque de memoire)
python manage.py migrate --noinput --verbosity 2 2>&1 || echo "MIGRATE ECHEC (code $?)"
python manage.py collectstatic --noinput 2>&1 || echo "COLLECTSTATIC ECHEC (code $?)"

# Premier compte admin d'une base vide (environnement de test) : seulement si les deux variables
# DJANGO_SUPERUSER_PHONE et DJANGO_SUPERUSER_PASSWORD existent, et jamais pour modifier un compte existant.
python - <<'PY' || echo "CREATION ADMIN ECHEC"
import os
phone = (os.environ.get("DJANGO_SUPERUSER_PHONE") or "").strip().replace(" ", "")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD") or ""
if phone and password:
    if phone.startswith("241"):
        phone = "+" + phone
    elif phone.startswith("0"):
        phone = "+241" + phone[1:]
    elif phone.isdigit() and len(phone) == 8:
        phone = "+241" + phone
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
    import django
    django.setup()
    from users.models import User
    if User.objects.filter(phone=phone).exists():
        print("Admin deja present", flush=True)
    else:
        User.objects.create_superuser(phone=phone, password=password, email="")
        print("Admin cree pour", phone[:7] + "...", flush=True)
PY
echo "Demarrage de gunicorn sur le port ${PORT:-8000}"

exec gunicorn wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers "${GUNICORN_WORKERS:-${WEB_CONCURRENCY:-3}}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-60}"
