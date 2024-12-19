from django.urls import path
from .views import LogEvent

urlpatterns = [
    path("log-event", LogEvent.as_view(), name="event_log"),
]
