import json

from .base_rest_service import BaseRestService
import logging
from django.conf import settings
logger = logging.getLogger(__name__)

class CEFRLevelService(BaseRestService):
    # todo - move settings to settings.py
    TIMEOUT = 100
    CONNECTION_TIMEOUT = 100

    def __init__(self, **kwargs):
        self.secret_token = settings.CEFR_LEVEL_SERVICE_AUTH_TOKEN
        super().__init__(**kwargs)

    def get_base_headers(self):
        return {"token": self.secret_token}

    def get_base_url(self) -> str:
        return settings.CEFR_LEVEL_SERVICE_ENDPOINT

    def cefr_level(self, *, text:str) -> str:
        data = {"text":text}
        response = self._post_request(url=f'{self.base_url}/predict', data=data)
        logger.info(f"Got result from cefr service -{response.status_code}- {response.content}")
        response_dict = json.loads(response.json())
        return response_dict.get("level")