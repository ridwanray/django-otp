#!/bin/sh
python manage.py makemigrations --no-input
python manage.py migrate --no-input
rm celerybeat.pid

exec "$@"