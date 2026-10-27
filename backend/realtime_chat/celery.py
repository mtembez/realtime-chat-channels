import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'realtime_chat.settings')

app = Celery('realtime_chat')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
