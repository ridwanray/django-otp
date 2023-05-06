from django.apps import apps, AppConfig
from django.conf import settings
import os
from celery import Celery
from decouple import config

if not settings.configured:
    environment = config('ENVIRONMENT')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', "core.settings."+environment) 

APP = Celery('core')


class CeleryConfig(AppConfig):
    name = 'core'
    verbose_name = 'Celery Config'

    def ready(self):
        APP.config_from_object('django.conf:settings', namespace='CELERY')
        installed_apps = [app_config.name for app_config in apps.get_app_configs()]
        APP.autodiscover_tasks(installed_apps, force=True)

    def tearDown(self):
        pass
