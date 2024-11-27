import logging
from django.conf import settings

try:
    from asgiref.local import Local
except ImportError:
    from threading import local as Local
from . import local, DEFAULT_NO_REQUEST_ID, LOG_REQUESTS_NO_SETTING




class RequestIDFilter(logging.Filter):

    def filter(self, record):
        default_request_id = getattr(settings, LOG_REQUESTS_NO_SETTING, DEFAULT_NO_REQUEST_ID)
        record.request_id = getattr(local, 'request_id', default_request_id)
        return True


class UserIdFilter(logging.Filter):

    def filter(self, record):
        record.user_id = getattr(local, 'user_id', 'NONUserId')
        return True
