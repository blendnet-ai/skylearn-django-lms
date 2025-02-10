from firebase_admin import auth
from rest_framework import authentication
from rest_framework import exceptions
from accounts.models import Student, User
from custom_auth.repositories import UserProfileRepository
from accounts.usecases import RoleAssignmentUsecase
from accounts.utils import generate_password
from django.contrib.auth.models import update_last_login


class FirebaseAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        id_token = request.headers.get("Authorization", "").replace("Bearer ", "")

        if not id_token or id_token == "":
            return None

        try:
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token["uid"]

            user, created = User.objects.get_or_create(
                firebase_uid=uid,
                defaults={
                    "email": decoded_token["email"],
                    "is_active": True,
                    "username": uid,
                    "first_name": decoded_token.get("name", "").split()[0] if decoded_token.get("name") else "",
                    "last_name": " ".join(decoded_token.get("name", "").split()[1:]) if decoded_token.get("name") else ""
                }
            )
            if created:
                user.set_password(generate_password())
                user.save()
            user_profile = UserProfileRepository.create_user_profile(user_id=user.id)
            if not user.is_student and not user.is_lecturer and not user.is_course_provider_admin:
                RoleAssignmentUsecase.assign_role_from_config(user)
            update_last_login(None, user)
            return (user, None)
        except Exception as e:
            print(str(e))
            raise exceptions.AuthenticationFailed("Invalid token")
