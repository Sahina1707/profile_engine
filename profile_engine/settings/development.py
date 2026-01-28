from .base import *  # noqa
from .base import INSTALLED_APPS, MIDDLEWARE

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

INSTALLED_APPS += []

MIDDLEWARE += []

CELERY_BROKER_URL = 'redis://127.0.0.1:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
# Example for Redis
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'