from typing import Optional, List, Dict
import time
from evaluation.event_flow.services.base_rest_service import BaseRestService
from django.conf import settings
import logging

class GitHubService(BaseRestService):
    def get_base_url(self) -> str:
        return settings.GITHUB_API_BASE_URL

    def get_base_headers(self) -> dict:
        return {"Authorization": f"Bearer {settings.GITHUB_API_TOKEN}"}

    def fetch_user_data(self, username: str) -> Optional[Dict]:
        url = f"{self.get_base_url()}/users/{username}"
        response = self._get_request(url=url)
        response.raise_for_status()
        return response.json()

    def fetch_contributions(self, username: str) -> Optional[List[Dict]]:
        url = f"{self.get_base_url()}/users/{username}/events/public"
        response = self._get_request(url=url)
        response.raise_for_status()
        return response.json()

    def get_api_calls_left(self) -> int:
        url = "https://api.github.com/rate_limit"
        response = self._get_request(url=url)
        response.raise_for_status()
        return response.json()["rate"]["remaining"]

    def get_time_left_to_recover(self) -> int:
        url = "https://api.github.com/rate_limit"
        response = self._get_request(url=url)
        response.raise_for_status()
        time_left_to_recover = (response.json()["rate"]["reset"] - time.time()) * 60
        return int(max(0, time_left_to_recover))

    @staticmethod
    def wait_for_api_calls_to_recover(time_left_to_recover: int) -> None:
        time_left_to_recover_minutes = time_left_to_recover / 60
        logging.info(f"No API calls left. Waiting for {time_left_to_recover_minutes:.2f} minutes to recover.")
        time.sleep(time_left_to_recover)