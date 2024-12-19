from django.urls import path
from .views import MarkAttendanceAndRedirect,GetJoiningUrl

urlpatterns = [
    path('join/<uuid:attendance_id>/', MarkAttendanceAndRedirect.as_view(), name='mark_attendance'),
    path('get-joining-url/<int:meeting_id>/',GetJoiningUrl.as_view(), name='get_joining_url')
]
