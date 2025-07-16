from django.views import View
from django.shortcuts import redirect
from django.http import Http404
from django.conf import settings
from meetings.models import AttendanceRecord
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import logging
from .usecases import MeetingAttendanceUseCase, MeetingUsecase
from rest_framework import status
from accounts.permissions import (
    IsLecturer,
    IsLoggedIn,
    IsStudent,
    IsCourseProviderAdminOrLecturer,
    IsSuperuser,
    firebase_drf_authentication,
)
from accounts.authentication import FirebaseAuthentication
from meetings.serializers import AdditionalRecordingSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Meeting, ReferenceMaterial
from .serializers import ReferenceMaterialSerializer
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.decorators import parser_classes
from rest_framework.decorators import api_view, permission_classes,authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from accounts.permissions import IsLoggedIn, IsCourseProviderAdminOrLecturer


logger = logging.getLogger(__name__)


class MarkAttendanceAndRedirect(APIView):
    def get(self, request, attendance_id):
        # Check if request is from Telegram bot
        user_agent = request.headers.get("User-Agent", "").lower()
        if "telegram" in user_agent or "telegrambot" in user_agent:
            return redirect(settings.FRONTEND_BASE_URL)
        else:
            meeting_link = MeetingAttendanceUseCase.mark_meeting_attendance(
                attendance_id
            )

        if meeting_link is None or len(meeting_link) < 5:
            return redirect(settings.FRONTEND_BASE_URL)
        return redirect(meeting_link)


class MarkAttendanceCommonURLAndRedirect(APIView):
    def get(self, request, reference_id):
        # Check if request is from Telegram bot
        user_agent = request.headers.get("User-Agent", "").lower()
        if "telegram" in user_agent or "telegrambot" in user_agent:
            return redirect(settings.FRONTEND_BASE_URL)
        else:
            meeting_link = MeetingAttendanceUseCase.mark_meeting_attendance_common_link(
                reference_id
            )

        if meeting_link is None or len(meeting_link) < 5:
            return redirect(settings.FRONTEND_BASE_URL)
        return redirect(meeting_link)


class GetCommonJoiningUrl(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request):
        user_id = request.user.id
        joining_url = MeetingAttendanceUseCase.get_common_joining_url(user_id)

        return Response({"joining_url": joining_url}, status=status.HTTP_200_OK)


class GetJoiningUrl(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, meeting_id):
        user_id = request.user.id
        meeting_id = meeting_id
        # user_id=46
        # meeting_id=117
        if meeting_id is None:
            return Response(
                {"error": "meeting_id required"}, status=status.HTTP_400_BAD_REQUEST
            )
        joining_url = MeetingAttendanceUseCase.get_joining_url(
            user_id=user_id, meeting_id=meeting_id
        )

        return Response({"joining_url": joining_url}, status=status.HTTP_200_OK)


class UploadAdditionalRecording(APIView):
    permission_classes = [IsLoggedIn, IsCourseProviderAdminOrLecturer]
    authentication_classes = [FirebaseAuthentication]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, meeting_id):
        """
        Upload additional recording for a meeting
        """
        serializer = AdditionalRecordingSerializer(data=request.data)

        if serializer.is_valid():
            try:
                filename = serializer.validated_data["filename"]

                # Upload recording using usecase
                blob_url = MeetingUsecase.upload_additional_recording(
                    meeting_id=meeting_id, filename=filename
                )

                return Response(
                    {
                        "message": "Recording Blob created successfully",
                        "blob_url": blob_url,
                    },
                    status=status.HTTP_201_CREATED,
                )

            except Exception as e:
                logger.error(f"Error uploading recording: {str(e)}")
                return Response(
                    {"error": f"Error uploading recording: {str(e)}"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteRecording(APIView):
    permission_classes = [IsLoggedIn, IsCourseProviderAdminOrLecturer]
    authentication_classes = [FirebaseAuthentication]

    def delete(self, request):
        """
        Delete a recording by its blob URL
        """
        blob_url = request.query_params.get("blob_url")
        if not blob_url:
            return Response(
                {"error": "blob_url is required as a query parameter"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            MeetingUsecase.delete_recording(blob_url)
            return Response(
                {"message": "Recording deleted successfully"}, status=status.HTTP_200_OK
            )
        except Exception as e:
            logger.error(f"Error deleting recording: {str(e)}")
            return Response(
                {"error": f"Error deleting recording: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
@api_view(['GET', 'POST'])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
@parser_classes([MultiPartParser, FormParser])
def reference_materials_list(request, meeting_id):
    from .serializers import ReferenceMaterialSerializer
    try:
        meeting = Meeting.objects.get(id=meeting_id)
    except Meeting.DoesNotExist:
        return Response({"error": "Meeting not found."}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        materials = meeting.reference_materials.all()
        serializer = ReferenceMaterialSerializer(materials, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        # Check if the user is a teacher or admin
        if not (request.user.is_lecturer or request.user.is_course_provider_admin):
            return Response({"error": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        
        data = request.data.copy()
        file = request.FILES.get('file')
        url = data.get('url')
        if file:
            data['material_type'] = 'file'
            data['url'] = ''  # or set to None
        elif url:
            data['material_type'] = 'link'
        else:
            return Response({"error": "Either file or url must be provided."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReferenceMaterialSerializer(data=data)
        if serializer.is_valid():
            serializer.save(meeting=meeting, uploaded_by=request.user, file=file if file else None)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn, IsCourseProviderAdminOrLecturer])
def reference_material_detail(request, material_id):
    
    try:
        material = ReferenceMaterial.objects.get(id=material_id)
    except ReferenceMaterial.DoesNotExist:
        return Response({"error": "Material not found."}, status=status.HTTP_404_NOT_FOUND)

    material.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)