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

# Site de test uniquement : copie (lecture seule) de la vraie base, une fois par demande
# (variables STAGING_COPY_FROM_DATABASE_URL et STAGING_COPY_REQUEST, voir la commande).
if [ "${STAGING_TEST_SHOP:-0}" = "1" ]; then
  python manage.py copy_prod_to_staging || echo "COPIE DE LA PRODUCTION ECHEC"
fi

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
# Site de test uniquement (STAGING_TEST_SHOP=1 dans render-staging.yaml) : boutique de test à 100 F.
if [ "${STAGING_TEST_SHOP:-0}" = "1" ]; then
  python manage.py seed_test_shop || echo "BOUTIQUE DE TEST ECHEC"
fi

echo "Demarrage de gunicorn sur le port ${PORT:-8000}"

exec gunicorn wsgi:application \
  --bind 0.0.0.0:${PORT:-8000} \
  --workers "${GUNICORN_WORKERS:-${WEB_CONCURRENCY:-3}}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-60}"
