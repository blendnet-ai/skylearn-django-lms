from rest_framework import status
from rest_framework.exceptions import APIException


class FirebaseError(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = "The user provided with the auth token is not a valid Firebase user, it has no Firebase UID"
    default_code = "no_firebase_uid"


class NoAuthToken(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "No authentication token provided."
    default_code = "no_auth_token"


class InvalidAuthToken(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Invalid or missing authentication token."
    default_code = "invalid_token"


class FirebaseUserNotFound(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = "Firebase user not found."
    default_code = "firebase_user_not_found"


class FirebaseAuthenticationFailed(APIException):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Firebase authentication failed."
    default_code = "firebase_authentication_failed"
