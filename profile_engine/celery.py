import os
from celery import Celery

# Change 'profile_engine.settings' to 'profile_engine.settings.base'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'profile_engine.settings.base')

app = Celery('profile_engine')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()