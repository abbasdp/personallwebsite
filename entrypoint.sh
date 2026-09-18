#!/bin/sh
set -e
mkdir -p "${DATA_DIR:-/data}/media"
python manage.py migrate --noinput
python manage.py import_seed --skip-if-exists
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model
User = get_user_model()
u = os.environ["DJANGO_SUPERUSER_USERNAME"]
p = os.environ["DJANGO_SUPERUSER_PASSWORD"]
e = os.environ.get("DJANGO_SUPERUSER_EMAIL", "abbasdp@proton.me")
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(u, e, p)
    print("superuser created")
else:
    print("superuser exists")
PY
fi
exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8080}" --workers 1 --threads 4 --timeout 60
