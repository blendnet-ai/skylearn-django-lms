from evaluation.event_flow.services.base_rest_service import BaseRestService
from evaluation.models import UserEvalQuestionAttempt
from django.conf import settings
import logging
from requests.exceptions import Timeout

logger = logging.getLogger(__name__)

#GLOT TIMEOUT LIMIT = 30 Sec
#Backup GLOT TIMEOUT LIMIT = 15 Sec
class TLEException(Exception):
    """Exception raised for time limit exceeded errors."""
    pass

class GlotService(BaseRestService):
    def __init__(self, timeout=40, connection_timeout=40):
        super().__init__(timeout=timeout, connection_timeout=connection_timeout)

    @staticmethod
    def get_image_from_language(language):
        mapping = {
            "python": "python",
            "java": "java",
            "javascript": "javascript",
            "cpp": "clang"
        }
        return f"glot/{mapping[language]}:latest"

    def get_base_url(self) -> str:
        return settings.GLOT_URL

    def get_base_headers(self) -> dict:
        return {"Authorization": f"Token {str(settings.GLOT_KEY)}"}

    def get_response_from_backup(self,language,payload):
        base_url = settings.SELF_HOSTED_GLOT_URL
        url = f"{base_url}/run"
        payload["image"] =  GlotService.get_image_from_language(language)
        payload["payload"] = {
            "language":language,
            **payload
        }
        headers = {"X-Access-Token": f"{str(settings.SELF_HOSTED_GLOT_KEY)}"}
        response = self._post_request(url=url, data=payload, custom_headers=headers)
        logger.info(f"Received response from backup Glot service: {response.status_code} {response.content}")
        if response.status_code == 400:
            logger.warning(f"Bad request to backup Glot service - {response.content}. Retrying...")
            response = self._post_request(url=url, data=payload, custom_headers=headers)
            logger.info(f"Received response from backup Glot service after retry: {response.status_code} {response.content}")
        return response

    def get_execution_result(self, language,code,file_name, inputs=None):
        language_to_extension = {
            'python': 'py',
            'java': 'java',
            'javascript': 'js',
            'ruby': 'rb',
            'go': 'go',
            'c': 'c',
            'cpp': 'cpp'
        }

        base_url=self.get_base_url()
        url = f"{base_url}/{language}/latest"
        payload = {
            'files': [
                {
                    'name': f'{file_name}.{language_to_extension[language]}',
                    'content': code
                }
            ]
        }
        
        if inputs:
            payload['stdin'] = inputs
        headers = self.get_base_headers()
        need_to_retry = False
        try:
            response = self._post_request(url=url, data=payload, custom_headers=headers)
            if response.status_code >= 500:
                logger.error(f"Error from Glot service - {response.content}. Status Code - {response.status_code}")
                need_to_retry = True
            if response.status_code == 400 and 'Max execution time exceeded' in response.json().get('message',''):
                raise TLEException("Execution time limit exceeded.")
        except Timeout:
            logger.error(f"Timeout from Glot service.")
            need_to_retry = True
        finally:
            if need_to_retry:
                response = self.get_response_from_backup(language=language, payload=payload)
                if 'limits.execution_time' in response.json().get('error',''):
                    raise TLEException("Execution time limit exceeded.")

        if 'limits.execution_time' not in response.json().get('error',''):
            response.raise_for_status()

        return response.json()