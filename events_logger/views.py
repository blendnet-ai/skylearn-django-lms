from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .repositories import PageEventRepository
from course.repositories import UploadRepository,UploadVideoRepository
from meetings.repositories import MeetingRepository
from accounts.permissions import (
    IsLecturer,
    IsLoggedIn,
    IsStudent,
    IsSuperuser,
    firebase_drf_authentication,
)
from accounts.authentication import FirebaseAuthentication
from accounts.models import User
from datetime import datetime, timedelta
from .usecases import LogEventUseCase



class LogEvent(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request):
        try:
            user=request.user
            # user = User.objects.get(id=46)  # This should be replaced with authenticated user
            event = LogEventUseCase.log_event(
                user=user,
                content_id=request.data.get('content_id'),
                content_type=request.data.get('content_type'),
                time_spent=request.data.get('time_spent')
            )
            return Response(
                {"message": "Event start entry logged.", "event_id": event.id}, 
                status=status.HTTP_201_CREATED
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)