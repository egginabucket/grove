# https://www.section.io/engineering-education/django-celery-tasks/
# https://testdriven.io/guides/django-celery/
# https://realpython.com/asynchronous-tasks-with-django-and-celery/


import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "celery_task.settings")
app = Celery("celery_task")
app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()
