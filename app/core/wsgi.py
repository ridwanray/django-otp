"""
WSGI config for lms project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/wsgi/
"""

import os
from decouple import config
from django.core.wsgi import get_wsgi_application

environment = config('ENVIRONMENT')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings."+environment)

application = get_wsgi_application()
