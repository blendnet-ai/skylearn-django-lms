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

        print(f"=== FIREBASE AUTH DEBUG ===")
        print(f"Request URL: {request.path}")
        print(f"Authorization header present: {'Authorization' in request.headers}")
        print(f"Token length: {len(id_token) if id_token else 0}")
        print(f"Token starts with: {id_token[:20] if id_token else 'None'}...")

        if not id_token or id_token == "":
            print("❌ No token provided")
            return None

        try:
            print("🔍 Attempting to verify Firebase token...")
            # First try with revocation checking
            try:
                decoded_token = auth.verify_id_token(id_token, check_revoked=True)
            except Exception as clock_error:
                if "too early" in str(clock_error) or "clock" in str(clock_error).lower():
                    print("⚠️ Clock sync issue detected, retrying without revocation check...")
                    decoded_token = auth.verify_id_token(id_token, check_revoked=False)
                else:
                    raise clock_error
            
            print(f"✅ Token verified successfully!")
            print(f"Token UID: {decoded_token.get('uid', 'No UID')}")
            print(f"Token email: {decoded_token.get('email', 'No email')}")
            
            uid = decoded_token["uid"]

            # Add retry logic for database operations
            max_retries = 3
            for attempt in range(max_retries):
                try:
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
                    print(f"User found/created: {user.email} (created: {created})")
                    
                    if created:
                        user.set_password(generate_password())
                        user.save()
                    user_profile = UserProfileRepository.create_user_profile(user_id=user.id)
                    if (not user.is_student and not user.is_lecturer and not user.is_course_provider_admin) or (user.needs_role_assignment):
                        RoleAssignmentUsecase.assign_role_from_config(user)
                    update_last_login(None, user)
                    print(f"✅ Authentication successful for user: {user.email}")
                    return (user, None)
                    
                except Exception as db_error:
                    if "database is locked" in str(db_error).lower() and attempt < max_retries - 1:
                        print(f"⚠️ Database locked, retrying... (attempt {attempt + 1}/{max_retries})")
                        import time
                        time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        print(f"❌ Database error after {attempt + 1} attempts: {str(db_error)}")
                        raise db_error
                        
        except Exception as e:
            print(f"❌ Firebase token verification failed: {str(e)}")
            print(f"Exception type: {type(e).__name__}")
            raise exceptions.AuthenticationFailed("Invalid token")
