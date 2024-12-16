from django.urls import path
from .views import (logEvent)

urlpatterns = [
    path("log-event", logEvent.as_view(), name="event_start"),
]
