"""
Celery application bootstrap for snedaEcommerceAPI.

Start a worker in a separate terminal with:
    celery -A snedaEcommerceAPI worker --loglevel=info

On Windows you MUST add the --pool=solo flag (no fork support):
    celery -A snedaEcommerceAPI worker --loglevel=info --pool=solo

to run celery beat run in seperate terminal on Windows
    celery -A snedaEcommerceAPI beat --loglevel=info

on linux you can run together
"""

import os
from celery import Celery

# Tell Celery which Django settings module to use
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'snedaEcommerceAPI.settings')

app = Celery('snedaEcommerceAPI')

# Pull all CELERY_* settings from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in every installed Django app
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
