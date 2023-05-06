#!/bin/sh
python manage.py makemigrations --no-input
python manage.py migrate --no-input
rm celerybeat.pid
rm logs/debug.log
exec "$@"