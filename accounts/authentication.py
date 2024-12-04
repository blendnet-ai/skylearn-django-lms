from firebase_admin import auth
from rest_framework import authentication
from rest_framework import exceptions
from accounts.models import Student, User
from custom_auth.repositories import UserProfileRepository
from accounts.usecases import RoleAssignmentUsecase
from accounts.utils import generate_password


class FirebaseAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        id_token = request.headers.get("Authorization", "").replace("Bearer ", "")

        if not id_token or id_token == "":
            return None

        try:
            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token["uid"]

            try:
                user = User.objects.get(firebase_uid=uid)
            except User.DoesNotExist:
                # Create user if not exists
                email = decoded_token["email"]
                user = User.objects.create(
                    firebase_uid=uid,
                    email=email,
                    is_active=True,
                    username=uid,
                )
                user.set_password(generate_password())
                user.save()
                RoleAssignmentUsecase.assign_role_from_config(user)
            user_profile = UserProfileRepository.create_user_profile(user_id=user.id)
            return (user, None)

        except Exception as e:
            print(str(e))
            raise exceptions.AuthenticationFailed("Invalid token")
