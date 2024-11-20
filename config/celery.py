import os
import time

from django.conf import settings
from celery import Celery
from celery.signals import setup_logging

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "speechai.settings")
from celery.signals import before_task_publish, task_prerun
from common.django_commons import local
import logging

logger = logging.getLogger(__name__)
app = Celery("speechai")


# if not settings.DEBUG:
#     import ddtrace
#     ddtrace.config.celery['distributed_tracing'] = True
#     ddtrace.config.celery['producer_service_name'] = 'django-celery-producer'
#     ddtrace.config.celery['worker_service_name'] = 'django-celery-worker'


# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY", force=True)


@before_task_publish.connect
def task_sending_handler(body=None, *args, **kwargs):
    """
    This function runs inside the thread of request, so it's 'local' has access to request_id and user_id, set by
    the RequestIDMiddleware. It sets those properties in kwargs, which will be used by task_prerun_handler.
    For that we manipulate the body tuple, whose 2 argument is kwargs dictionary.
    It would be useful to find a reference from celery documentation that this manipulation is allowed and won't
    break in future
    """
    request_id = getattr(local, "request_id", "none")
    user_id = getattr(local, "user_id", "NONUserId-Celery")
    body_kwargs = body[1]
    body_kwargs["request_id"] = request_id
    body_kwargs["user_id"] = user_id


@task_prerun.connect
def task_prerun_handler(*args, **kwargs):
    """
    This function gets relevant kwargs put by task_sending_handler in kwargs and puts them into local of the
    """
    request_id = kwargs.get("kwargs").pop("request_id", "none")
    user_id = kwargs.get("kwargs").pop("user_id", "none")
    setattr(local, "request_id", request_id)
    setattr(local, "user_id", user_id)


@setup_logging.connect
def config_loggers(*args, **kwags):
    from logging.config import dictConfig
    from django.conf import settings

    dictConfig(settings.LOGGING)


# Load task modules from all registered Django apps.


app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self, **kwargs):
    logger.info(f"TASK KWARGS START {kwargs}")
    time.sleep(4)
    logger.info(f"TASK KWARGS STOP| {kwargs}")
