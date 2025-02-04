from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from django.core.cache import cache
from django.conf import settings

from Feedback.serializers import FeedbackResponseSerializer
from Feedback.usecases import FeedbackFormUsecase,FeedbackResponseUsecase
from custom_auth.authentication import FirebaseAuthentication
from Feedback.repositories import FeedbackFormRepository
from datetime import datetime


class FeedbackFormView(APIView):
    permission_classes = [IsAuthenticated]

    authentication_classes = [FirebaseAuthentication]

    def get(self, request, _=None):
        user_id = request.user.id
        name = request.query_params.get("name")
        feedback_form_data = FeedbackFormUsecase.get_form_by_name(name=name)
        return Response({"data": feedback_form_data}, status=status.HTTP_200_OK)

    def post(self, request, _=None):
        serializer = FeedbackResponseSerializer(data=request.data)
        user_id = request.user.id
        if serializer.is_valid():
            serializer.save(user_id=user_id)
            return Response(
                {"data": "Feedback response submitted successfully."},
                status=status.HTTP_201_CREATED,
            )


        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserFeedbackStatusView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, _=None):
        #from django.contrib.auth import get_user_model
        # User = get_user_model()
        # user_id = User.objects.get(id=31)
        user=request.user
        current_date = datetime.now().date()
        data=FeedbackResponseUsecase.get_forms_status(user, current_date)
        return Response(data)


