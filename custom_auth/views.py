from pyexpat.errors import messages
from urllib import request
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
import random

from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
import rest_framework.exceptions as rest_framework_exceptions
from rest_framework.permissions import AllowAny

# from speechai.settings import DOUBT_SOLVING_ORG_API_KEY
# from InstituteConfiguration.repositories import QuestionListRepository
from accounts.authentication import FirebaseAuthentication
from accounts.permissions import IsLoggedIn
from custom_auth.serializers import (
    ActivityDataSerializer,
    UserSerializer,
    FormFetchSerializer,
    FormSubmitSerializer,
)
from custom_auth.usecases import (
    ActivityDataUseCase,
    OnBoardingUsecase,
    SignUpUsecase,
    OnBoardingUsecase,
)
from data_repo.repositories import ConfigMapRepository
from services.sms_service import SMS2FactorService
from .repositories import FormRepository, UserProfileRepository
from django.views.generic.base import TemplateView
import logging
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from config.settings import TWO_Factor_SMS_API_KEY, TELEGRAM_BOT_NAME
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper
from django.contrib.auth.decorators import login_required
import re
from rest_framework.decorators import (
    authentication_classes,
    permission_classes,
    api_view,
)

logger = logging.getLogger(__name__)

User = get_user_model()
SMS2FactorService = SMS2FactorService(api_key=TWO_Factor_SMS_API_KEY)  # 2

# GDWrapperIntance=GDWrapper("1gKG2xj6o5xiHV6NexfWowh8FNuVAK_ZOQWoPc05CjYs")

from django.views.decorators.csrf import csrf_exempt

from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from accounts.permissions import FirebaseAuthentication, IsLoggedIn
from rest_framework.permissions import IsAuthenticated


class FormCRUD(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        data = FormFetchSerializer(data=request.query_params)
        data.is_valid(raise_exception=True)

        form_data = FormRepository.fetch_form(data.validated_data.get("form_name"))

        return Response({"data": form_data}, status=status.HTTP_200_OK)

    def post(self, request, format=None):
        data = FormSubmitSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        # Sanchit-TODO - Temporary for onbaording form. Move to form specific validator OR create a dedicated
        # serializer + view based on exact requirement.
        # form_data = data.validated_data.get("user_data").get("data", None)
        # onboarding_code = form_data.get("sections")[0]["fields"][0]["value"]
        # if onboarding_code != ConfigMapRepository.get_config_by_tag(tag=ConfigMapRepository.ON_BOARDING_CODES).get(
        #         "admin"):
        #     raise rest_framework_exceptions.PermissionDenied("Invalid on-boarding code.")
        user_id = request.user.id
        UserProfileRepository.save_user_data(
            user_id,
            data.validated_data.get("form_name"),
            data.validated_data.get("user_data").get("data"),
        )
        return Response(
            {"message": "User data saved successfully"}, status=status.HTTP_200_OK
        )


class FetchUserData(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        user_id = request.user.id

        user_data = UserProfileRepository.fetch_user_data(user_id)
        user_data["has_lab"] = UserProfileRepository.has_lab(user_id=user_id)

        return Response({"data": user_data}, status=status.HTTP_200_OK)


class UserProfileApiView(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        user = request.user
        user_serializer = UserSerializer(user)

        return Response(user_serializer.data)


class UserListApiView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        users = User.objects.filter(is_active=True, is_staff=False).order_by(
            "-date_joined"
        )
        user_serializer = UserSerializer(users, many=True)

        return Response(user_serializer.data)


class ActivityDataView(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        activity_data = ActivityDataUseCase.get_and_update_activity_data(
            user_id=request.user.id
        )

        activity_data_serializer = ActivityDataSerializer(activity_data)
        return Response(activity_data_serializer.data)


class SignUpView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, format=None):
        data = request.data
        email = data.get("email", None)

        error_message = SignUpUsecase.sign_up(email=email)

        if error_message:
            return Response(
                {"error": error_message}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": "Sign-up successful"}, status=status.HTTP_201_CREATED
        )


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def get_onboarding_status(request):
    user = request.user
    onboarding_status = OnBoardingUsecase.get_onboaring_status(user)
    return Response(onboarding_status, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def determine_onboarding_step(request):
    user_id = request.user.id
    step = OnBoardingUsecase.determine_onboarding_step(user_id)
    return Response({"step": step}, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def send_otp(request):
    user = request.user
    phone_number = request.data.get("phone_number")

    if not phone_number:
        return Response(
            {"error": "Phone number is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    otp_sending_result = OnBoardingUsecase.handle_otp_sending(user, phone_number)

    if otp_sending_result.get("otp_sent"):
        return Response(otp_sending_result, status=status.HTTP_200_OK)
    else:
        return Response(otp_sending_result, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def verify_otp(request):
    user = request.user
    entered_otp_value = request.data.get("otp_value")
    code = request.data.get("code")
    phone_number=request.data.get("phone_number")

    if not entered_otp_value:
        return Response(
            {"error": "OTP value is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    if not phone_number:
        return Response(
            {"error": "Phone number is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    onboarding_verification_result = OnBoardingUsecase.handle_otp_verification(
        user, code, entered_otp_value,phone_number
    )

    if onboarding_verification_result.get("otp_verified"):
        return Response(onboarding_verification_result, status=status.HTTP_200_OK)
    else:
        return Response(
            onboarding_verification_result, status=status.HTTP_400_BAD_REQUEST
        )

@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def cv_upload(request):
    cv_link = request.data.get("link")
    linkedin_link = request.data.get("linkedin_link")
    upload_status = request.data.get("status")

    if not cv_link and not linkedin_link and upload_status == "filled":
        return Response(
            {"error": "Either Upload resume or linkedin Link is missing "}, status=status.HTTP_400_BAD_REQUEST
        )

    cv_upload_result = OnBoardingUsecase.add_cv_upload_link(request.user, cv_link, linkedin_link, upload_status)

    return Response(cv_upload_result, status=status.HTTP_200_OK)

@api_view(["POST"])
@authentication_classes([FirebaseAuthentication])
@permission_classes([IsLoggedIn])
def skip_telegram_onboarding(request):
    user=request.user
    
    if user.is_lecturer:
        skip_telegram_onboarding_result=OnBoardingUsecase.skip_telegram_onboarding(request.user)
        return Response(skip_telegram_onboarding_result, status=status.HTTP_200_OK)
    else:
        return Response({"telegram_skipped":False,"message":"Only lecturer can skip telegram onboarding"}, status=status.HTTP_200_OK)
        

# @csrf_exempt
# @api_view(['POST'])
# def fetch_filled_data(request):
#     user = request.user
#     data_fetching_result = OnBoardingUsecase.handle_fetching_filled_data(user)
#     return Response(data_fetching_result, status=status.HTTP_200_OK)
