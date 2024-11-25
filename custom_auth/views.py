from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
import rest_framework.exceptions as rest_framework_exceptions
from rest_framework.permissions import AllowAny
from speechai.settings import DOUBT_SOLVING_ORG_API_KEY
from InstituteConfiguration.repositories import QuestionListRepository
from custom_auth.authentication import FirebaseAuthentication, HardcodedAuthentication
from custom_auth.serializers import ActivityDataSerializer, UserSerializer, FormFetchSerializer, FormSubmitSerializer
from custom_auth.usecases import ActivityDataUseCase, SignUpUsecase,DoubtSolvingTokenUseCase
from data_repo.repositories import ConfigMapRepository
from .repositories import FormRepository, UserProfileRepository
import logging

logger = logging.getLogger(__name__)

User = get_user_model()

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

class DoubtSolvingTokenView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]
    
    def get(self, request, format=None):
        user_id=request.user.id
        data=DoubtSolvingTokenUseCase.create_or_get_token(user_id,DOUBT_SOLVING_ORG_API_KEY)
        if data is None:
            return Response(
            {"message": "Something went wrong"},
            status=status.HTTP_400_BAD_REQUEST
        )
        return Response(
            {"data": data},
            status=status.HTTP_200_OK
        )
        
    