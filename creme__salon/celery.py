import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "creme_salon.settings")

app = Celery("creme_salon")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
