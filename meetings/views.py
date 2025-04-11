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
    # permission_classes = [IsLoggedIn, IsCourseProviderAdminOrLecturer]
    # authentication_classes = [FirebaseAuthentication]
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
