from .base import *
from decouple import config

ALLOWED_HOSTS = ['*']

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('SMTP_HOST')
EMAIL_HOST_USER =config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD =config('EMAIL_HOST_PASSWORD')
EMAIL_PORT = 587
EMAIL_USE_TLS = True

PASSWORD_RESET_TIMEOUT_DAYS = 1

LOGGING = {}