from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proyecto_torneo_f5.settings')

app = Celery('proyecto_torneo_f5')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Agregá esto para usar django-celery-beat
from celery.schedules import crontab
app.conf.beat_scheduler = 'django_celery_beat.schedulers:DatabaseScheduler'

app.conf.enable_utc = True
app.conf.timezone = "America/Argentina/Buenos_Aires"
# o en settings:
CELERY_ENABLE_UTC = True
CELERY_TIMEZONE = "America/Argentina/Buenos_Aires"