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
from custom_auth.authentication import FirebaseAuthentication, HardcodedAuthentication
from custom_auth.serializers import ActivityDataSerializer, UserSerializer, FormFetchSerializer, FormSubmitSerializer
from custom_auth.usecases import ActivityDataUseCase, OnBoardingUsecase, SignUpUsecase, OnBoardingUsecase
from data_repo.repositories import ConfigMapRepository
from services.sms_service import SMS2FactorService
from .repositories import FormRepository, UserProfileRepository
from django.views.generic.base import TemplateView
import logging
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from config.settings import TWO_Factor_SMS_API_KEY,TELEGRAM_BOT_NAME
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper
from django.contrib.auth.decorators import login_required
import re

logger = logging.getLogger(__name__)

User = get_user_model()
SMS2FactorService = SMS2FactorService(api_key=TWO_Factor_SMS_API_KEY)#2
print(TWO_Factor_SMS_API_KEY)
GDWrapperIntance=GDWrapper("1gKG2xj6o5xiHV6NexfWowh8FNuVAK_ZOQWoPc05CjYs")

class FormCRUD(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]
    
    def get(self, request, format=None):
        data = FormFetchSerializer(data=request.query_params)
        data.is_valid(raise_exception=True)

        form_data = FormRepository.fetch_form(data.validated_data.get('form_name'))

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
        UserProfileRepository.save_user_data(user_id, data.validated_data.get('form_name'),
                                             data.validated_data.get('user_data').get('data'))
        return Response({"message": "User data saved successfully"}, status=status.HTTP_200_OK)


class FetchUserData(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        user_id = request.user.id

        user_data = UserProfileRepository.fetch_user_data(user_id)
        user_data["has_lab"] = UserProfileRepository.has_lab(user_id=user_id)

        return Response({"data": user_data}, status=status.HTTP_200_OK)


class UserProfileApiView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        user = request.user
        user_serializer = UserSerializer(user)

        return Response(user_serializer.data)


class UserListApiView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        users = User.objects.filter(is_active=True,
                                    is_staff=False).order_by('-date_joined')
        user_serializer = UserSerializer(users, many=True)

        return Response(user_serializer.data)


class ActivityDataView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        activity_data = ActivityDataUseCase.get_and_update_activity_data(user_id=request.user.id)

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
                {"error": error_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {"message": "Sign-up successful"},
            status=status.HTTP_201_CREATED
        )


@login_required
def OnBoardingView(request):
    user = request.user
    user_id=user.id
    onboarding_details = OnBoardingUsecase.get_onboaring_status(user_id)
    if not onboarding_details.get('telegram_status',False):
        messages.error(request,"Complete telegram onboarding first")
        
    # Determine the current onboarding step
    step= OnBoardingUsecase.determine_onboarding_step(user_id)
    if step == "dashboard":
        return redirect('dashboard')

    # Prepare context for rendering
    context = {
        'onboarding_details': onboarding_details,
        'step': step
    }

    # Clear messages after they are retrieved
    messages.get_messages(request)

    # Handle POST requests for OTP verification and detail verification
    if request.method == 'POST':
        if 'send_otp' in request.POST:
            phone_number = request.POST.get('phone_number')
            otp_sending_result=OnBoardingUsecase.handle_otp_sending(user,phone_number)
            if otp_sending_result.get('otp_sent'):
                messages.success(request, otp_sending_result.get('message'))
                return redirect('onboarding')
            else:
                messages.success(request, otp_sending_result.get('message'))
                return redirect('onboarding')
        if 'verify_otp' in request.POST:
            entered_otp_value = request.POST.get('otp_value')
            onboarding_verification_result=OnBoardingUsecase.handle_otp_verification(user, entered_otp_value)
            if onboarding_verification_result.get('otp_verified'):
                messages.success(request, onboarding_verification_result.get('message'))
                return redirect('onboarding')
            else:
                messages.success(request, onboarding_verification_result.get('message'))
                return redirect('onboarding')
                
        elif 'verify_details' in request.POST:
            data_fetching_result=OnBoardingUsecase.handle_fetching_filled_data(user)
            if data_fetching_result.get('onboarding_data_fetched'):
                messages.success(request, "Onboarding completed successfully.")
                return redirect('dashboard')
            else:
                messages.error(request, "Data not found. Make sure you have filled the form.")
                return redirect('onboarding')

    messages.get_messages(request)
    return render(request, "onboarding/onboarding.html", context)









        
        
        
    
    