from data_repo.models import ConfigMap
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from custom_auth.authentication import FirebaseAuthentication
from data_repo.providers.feedbackform import FeedbackFormProvider
from data_repo.providers.referral import ReferralProvider
from django.shortcuts import get_object_or_404
from .repositories import InstituteDataRepository

class ProfilePageContent(APIView):
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        response = {
            "feedback_form": FeedbackFormProvider.get_feedback_form_url(),
            "referral_msg": ReferralProvider.get_referral_message(),
            "referral_url": ReferralProvider.get_referral_url()
        }
        return Response(response, status=status.HTTP_200_OK)


class ConfigMapAPIView(APIView):
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, _, tag):
        config_map = get_object_or_404(ConfigMap, tag=tag, is_active=True)

        return Response(config_map.config)


class InstituteNameAutoFill(APIView):
    authentication_classes = [FirebaseAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, format=None):
        institute_name = request.query_params.get('institute_name', None)
        if institute_name is None:
            return Response({"error": "institute_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        response = []
        institute_data = InstituteDataRepository.search_institutes_by_name(institute_name)
        
        for data in institute_data:
            response.append(data.institute_name)
        return Response(response, status=status.HTTP_200_OK)