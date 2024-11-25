from CVEvaluation.layers import ResumeJSONFormatConverter
from custom_auth.services.custom_auth_service import CustomAuth
from django.conf import settings
from evaluation.event_flow.services.base_rest_service import BaseRestService
import requests
from CVEvaluation.usecases import SavedResumeDataRetrieval

class ResumeBuilderService(BaseRestService):
    def get_base_url(self) -> str:
        return settings.RESUME_APP_BACKEND_URL

    def get_base_headers(self) -> dict:
        return {}

    def build_resume(self, user_id,resume_id):
        saved_json=SavedResumeDataRetrieval.get_resume_data(resume_id)
        converted_json={}
        if saved_json:
            converted_json = ResumeJSONFormatConverter.convert_gpt_json_to_resume_json_format(saved_json)
            converted_json['state']='completed'
        else:
            converted_json['state']='failed'

        firebase_token = CustomAuth().get_firebase_token(uid=user_id)
        headers = {"Authorization": f"Bearer {firebase_token}"}
        url = f"{settings.RESUME_APP_BACKEND_URL}/resume/{resume_id}"
        response = self._patch_request(url=url, data={'data':converted_json}, custom_headers=headers)
        response.raise_for_status()
        return response.json() 
    
    def get_all_reumses(self,user_id,email_list):
        firebase_token = CustomAuth().get_firebase_token(uid=user_id)
        headers = {"Authorization": f"Bearer {firebase_token}"}
        url = f"{settings.RESUME_APP_BACKEND_URL}/resume/fetchall"
        response = self._post_request(url=url, data={'data':{'emails':email_list}}, custom_headers=headers)
        return response.json() 