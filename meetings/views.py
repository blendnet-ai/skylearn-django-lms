from django.views import View
from django.shortcuts import redirect
from django.http import Http404
from django.conf import settings
from meetings.models import AttendanceRecord
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging
from .usecases import MeetingAttendanceUseCase
from rest_framework import status
from accounts.permissions import (
    IsLecturer,
    IsLoggedIn,
    IsStudent,
    IsSuperuser,
    firebase_drf_authentication,
)
from accounts.authentication import FirebaseAuthentication

logger = logging.getLogger(__name__)

class MarkAttendanceAndRedirect(APIView):
    def get(self, request, attendance_id):
        meeting_link=MeetingAttendanceUseCase.mark_meeting_attendance(attendance_id)
        if meeting_link is None or len(meeting_link) <5:
            return redirect(settings.FRONTEND_BASE_URL)
        return redirect(meeting_link)

class MarkAttendanceCommonURLAndRedirect(APIView):
    def get(self, request, user_id):
        user_id=user_id
        meeting_link=MeetingAttendanceUseCase.mark_meeting_attendance_common_link(user_id)
        if meeting_link is None or len(meeting_link) <5:
            return redirect(settings.FRONTEND_BASE_URL)
        return redirect(meeting_link)

class GetCommonJoiningUrl(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    def get(self, request):
        user_id=request.user.id
        joining_url=MeetingAttendanceUseCase.get_common_joining_url(user_id)
        
        return Response({
            'joining_url': joining_url
        }, status=status.HTTP_200_OK)


class GetJoiningUrl(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    def get(self, request,meeting_id):
        user_id=request.user.id
        meeting_id=meeting_id
        # user_id=46
        # meeting_id=117
        if meeting_id is None:
            return Response({'error':'meeting_id required'},status=status.HTTP_400_BAD_REQUEST)
        joining_url=MeetingAttendanceUseCase.get_joining_url(user_id=user_id,meeting_id=meeting_id)
        
        return Response({
            'joining_url': joining_url
        }, status=status.HTTP_200_OK)
            