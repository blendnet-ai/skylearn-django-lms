# myapp/services/firebase_service.py

import os
from django.contrib.auth import get_user_model
from django.conf import settings
from firebase_admin import credentials, auth
from firebase_admin import initialize_app
from firebase_admin._auth_utils import UserNotFoundError
from evaluation.event_flow.services.base_rest_service import BaseRestService
from datetime import datetime

User = get_user_model()

class CustomAuth(BaseRestService):
    def get_base_url(self) -> str:
        return settings.IDENTITY_TOOLKIT_API_URL

    def get_base_headers(self) -> dict:
        return {}

    def get_firebase_token(self,uid):
        userData = User.objects.get(id=uid)
        additional_claims = {
            "user_id": userData.username
        }
        custom_token = auth.create_custom_token(str(userData.username), additional_claims)
        api_key = settings.FIREBASE_API_KEY
        url = f"{self.base_url}/accounts:signInWithCustomToken?key={api_key}"
        payload = {"token": custom_token.decode("utf-8"), "returnSecureToken": True}
        response = self._post_request(url=url, data=payload)
        response_data = response.json()
        if "idToken" in response_data:
            return response_data["idToken"]
        else:
            raise Exception(
                "Error signing in with custom token: "
                + response_data.get("error", {}).get("message", "Unknown error")
            )

    def create_user(email, password):
        user = auth.create_user(email=email, password=password)
        return user.uid
    
    def get_user_by_email(email):
        return auth.get_user_by_email(email).uid
    
    def get_user_latest_login(uid):
        try:
            user = auth.get_user(uid)
            last_login = user.user_metadata.last_refresh_timestamp
            last_login_str = datetime.fromtimestamp(last_login / 1000)
            return last_login_str
        except UserNotFoundError:
            return None
