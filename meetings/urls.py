from django.urls import path
from .views import MarkAttendanceAndRedirect,GetJoiningUrl,GetCommonJoiningUrl,MarkAttendanceCommonURLAndRedirect

urlpatterns = [
    path('join/<uuid:attendance_id>/', MarkAttendanceAndRedirect.as_view(), name='mark_attendance'),
    path('get-joining-url/<int:meeting_id>/',GetJoiningUrl.as_view(), name='get_joining_url'),
    path('join-meeting/<int:user_id>/', MarkAttendanceCommonURLAndRedirect.as_view(), name='join_meeting'), #common url marking attendance
    path('get-meeting-url/', GetCommonJoiningUrl.as_view(), name='get_meeting_url'),#common url get meetingn url

]
