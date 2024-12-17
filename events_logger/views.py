from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .repositories import PageEventRepository
from course.repositories import UploadRepository,UploadVideoRepository
from accounts.permissions import (
    IsLecturer,
    IsLoggedIn,
    IsStudent,
    IsSuperuser,
    firebase_drf_authentication,
)
from accounts.authentication import FirebaseAuthentication
from accounts.models import User
from datetime import datetime



class logEvent(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request):
        content_id = request.data.get('content_id')
        content_type=request.data.get('content_type')
        time_spent=request.data.get('time_spent')
        current_date = datetime.now().date()

        if not content_id or not content_type:
            return Response({"error": "content_id and content_type are required."}, status=status.HTTP_400_BAD_REQUEST)

        if content_type=="reading":
            upload=UploadRepository.get_reading_resource_by_id(resource_id=content_id)
            if not upload:
                return Response({"error": "Content not found"}, status=status.HTTP_400_BAD_REQUEST)
            event,created=PageEventRepository.get_or_create_page_event(user,current_date,True,time_spent,upload,None)

            if not created:
                event=PageEventRepository.add_time_to_user_time(event,time_spent)
        elif content_type=="video":
            upload_video=UploadVideoRepository.get_video_resource_by_id(resource_id=content_id)
            if not upload_video:
                return Response({"error": "Content not found"}, status=status.HTTP_400_BAD_REQUEST)
            event,created=PageEventRepository.get_or_create_page_event(user,current_date,True,time_spent,None,upload_video)
            if not created:
                event=PageEventRepository.add_time_to_user_time(event,time_spent)
        

        return Response({"message": "Event start entry logged.", "event_id": event.id}, status=status.HTTP_201_CREATED)