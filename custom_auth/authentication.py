from channels.db import database_sync_to_async
import logging
import typing
import json
from django.contrib.auth import get_user_model
from firebase_admin import auth
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from custom_auth import exceptions
from common.django_commons import local
from custom_auth.usecases import BetaUserlistUsecase
from .repositories import UserProfileRepository
# from DoubtSolving.usecases import ValidateApiKeyUseCase,ValidateUserKeyUseCase


logger = logging.getLogger(__name__)

User = get_user_model()

# class APIKeyAuthentication(BaseAuthentication):
#     """API BASED Authentication for Django Rest Framework"""
#     def authenticate(self, request):
#         api_key = request.headers.get('Api-Key') 
#         if not api_key:
#             raise AuthenticationFailed('Please provide Api-Key in headers')
        
#         is_valid,organization = ValidateApiKeyUseCase.is_api_key_valid(api_key)
#         if is_valid:
#             organization.is_authenticated = True
#             return organization, None  
#         else:
#             raise AuthenticationFailed('Invalid API key')

# class UserKeyAuthentication(BaseAuthentication):
#     """API BASED Authentication for Django Rest Framework"""
#     def authenticate(self, request):
#         user_key = request.headers.get('User-Key') 
#         if not user_key:
#             raise AuthenticationFailed('Please provide User-Key in headers')
        
#         user_id = request.headers.get('User-Id') 
#         if not user_id:
#             raise AuthenticationFailed('Please provide User-Id in headers')
        
#         is_valid,is_expired,user_mapping = ValidateUserKeyUseCase.is_user_key_valid(user_id,user_key)
#         if is_valid:
#             user_mapping.is_authenticated = True
#             return user_mapping, None 
#         elif is_expired:
#             raise AuthenticationFailed('The provided user key is expired or invalid. Please verify and try again.')
#         else:
#             raise AuthenticationFailed('Invalid User key')
        

class HardcodedAuthentication(BaseAuthentication):
    """Custom Firebase Authentication for Django Rest Framework"""

    def authenticate(self, request):
        """Authenticate the request using Firebase token"""
        user = User.objects.get(username="yasirmansoori")
        # print(user)
        local.user_id = user.id
        return user, None


class FirebaseAuthentication(BaseAuthentication):
    """Custom Firebase Authentication for Django Rest Framework"""

    @classmethod
    def get_uid_and_email_from_headers(cls, headers_dict: typing.Dict, access_point: str = None):

        if isinstance(headers_dict, list):
            headers_dict = dict(headers_dict)
            headers_dict = {key.decode('utf-8'): value.decode('utf-8')
                            for key, value in headers_dict.items()}

        if access_point == "websocket":
            auth_header = headers_dict.get(
                "sec-websocket-protocol") or headers_dict.get('Sec-WebSocket-Protocol')
            if not auth_header:
                logger.warning("No auth token provided")
                raise exceptions.NoAuthToken("No auth token provided")
            auth_header_list = auth_header.strip('][').split(', ')
            id_token = auth_header_list[1]
            id_token = id_token.replace('"', '')
        else:
            auth_header = headers_dict.get("Authorization") or headers_dict.get(
                'authorization')  # Use headers.get() for case insensitivity
            if not auth_header:
                logger.warning("No auth token provided")
                raise exceptions.NoAuthToken("No auth token provided")
            # Split the authorization header to extract the token
            header_parts = auth_header.split(" ")

            if len(header_parts) != 2:
                logger.warning("Invalid auth token format")
                raise exceptions.InvalidAuthToken("Invalid auth token format")

            token_type, id_token = header_parts

            if token_type.lower() != "bearer":
                logger.warning(
                    "Invalid auth token - Token type is not 'Bearer'")
                raise exceptions.InvalidAuthToken("Token type is not 'Bearer'")

        # Decode the Firebase ID token
        decoded_token = None
        try:
            decoded_token = auth.verify_id_token(id_token)
        except auth.ExpiredIdTokenError:
            logger.warning("Expired auth token")
            raise exceptions.InvalidAuthToken("Expired auth token")
        except auth.InvalidIdTokenError:
            logger.warning("Invalid auth token")
            raise exceptions.InvalidAuthToken("Invalid auth token")
        except auth.CertificateFetchError:
            logger.warning("Firebase authentication failed")
            raise exceptions.FirebaseAuthenticationFailed()
        except Exception as exp:
            logger.warning(
                f"An error occurred during authentication: {str(exp)}")
            raise exceptions.FirebaseError()

        # Return None if the token or decoded token is invalid
        if not decoded_token:
            logger.warning("Invalid Decoded Token")
            raise exceptions.FirebaseAuthenticationFailed()

        # Get the UID of the user
        try:
            uid = decoded_token['uid']
        except Exception as exp:
            logger.warning(
                f"An error occurred during authentication: {str(exp)}")
            raise exceptions.FirebaseError()

        email = decoded_token.get('email', '')
        return uid, email

    def authenticate(self, request):
        """Authenticate the request using Firebase token"""
        """
        If ever need to put authentication in middleware, eg for logging user id or do common tasks for user before and 
        after request  AND still use this only for DRF handling of auth, see below comment 
        "You can use request._request.user in drf authentication classes to get the user authenticated by django, 
        and it won't query again since django has cached it in django request object, hope it helps."
        - ref https://github.com/encode/django-rest-framework/discussions/7770#discussioncomment-6943405
        """
        # Get the authorization token from the request header
        headers_dict = request.headers
        uid, email = self.get_uid_and_email_from_headers(headers_dict)
        # Get or create the user based on the UID
        user, created = User.objects.get_or_create(
            username=uid, defaults={'email': email})
        if created:
            UserProfileRepository.create_user_profile(user_id=user.id)
            BetaUserlistUsecase.mark_onboarding_complete_if_whitelisted_user(
                email=email, user_id=user.id)
            BetaUserlistUsecase.mark_onboarding_complete_and_assign_institue_if_in_institue_student_list(
                email=email, user_id=user.id)
            # BetaUserlistUsecase.mark_onboarding_complete_for_user_if_not(
            #     email=email, user_id=user.id)
            # BetaUserlistUsecase.assign_institute_based_on_email_domain(
            #     email=email, user_id=user.id)
        local.user_id = user.id
        logger.info(f"Request made. url = {request.path} ")
        return user, None

    def authenticate_token(token):
        try:
            decoded_token = auth.verify_id_token(token)
        except auth.ExpiredIdTokenError:
            logger.warning("Expired auth token")
            raise exceptions.InvalidAuthToken("Expired auth token")
        except auth.InvalidIdTokenError:
            logger.warning("Invalid auth token")
            raise exceptions.InvalidAuthToken("Invalid auth token")
        except auth.CertificateFetchError:
            logger.warning("Firebase authentication failed")
            raise exceptions.FirebaseAuthenticationFailed()
        except Exception as exp:
            logger.warning(
                f"An error occurred during authentication: {str(exp)}")
            raise exceptions.FirebaseError()

        # Return None if the token or decoded token is invalid
        if not decoded_token:
            logger.warning("Invalid Decoded Token")
            return None

        # Get the UID of the user
        try:
            uid = decoded_token['uid']
        except Exception as exp:
            logger.warning(
                f"An error occurred during authentication: {str(exp)}")
            raise exceptions.FirebaseError()

        email = decoded_token.get('email', '')
        # Get or create the user based on the UID
        user, created = User.objects.get_or_create(
            username=uid, defaults={'email': email})

        return user, None


@database_sync_to_async
def get_user(headers_dict: typing.Dict):
    uid, email = FirebaseAuthentication.get_uid_and_email_from_headers(
        headers_dict, access_point="websocket")
    user, created = User.objects.get_or_create(
        username=uid, defaults={'email': email})
    # user = User.objects.get(id=1)
    return user


class FirebaseAuthMiddleware:
    """
    Custom middleware (insecure) that takes user IDs from the query string.
    """

    def __init__(self, app):
        # Store the ASGI application we were passed
        self.app = app

    async def __call__(self, scope, receive, send):
        # Look up user from query string (you should also do things like
        # checking if it is a valid user ID, or if scope["user"] is already
        # populated).
        scope['user'] = await get_user(scope["headers"])
        return await self.app(scope, receive, send)


class IsPartnerAdminUser(BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and UserProfileRepository.is_partner_admin_user(request.user.id))
