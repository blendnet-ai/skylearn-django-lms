from datetime import datetime, timedelta
from venv import logger
import requests
from typing import Dict, Any, Optional
from django.core.cache import cache
from django.conf import settings
from .base import BaseConferencePlatformService, MeetingDetails, Presenter


class MSTeamsConferencePlatformService(BaseConferencePlatformService):
    AUTH_URL = f"https://login.microsoftonline.com/{settings.MS_TEAMS_TENANT_ID}/oauth2/v2.0/token"
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0/users/{user_id}/onlineMeetings"
    MEETING_ID_URL= "https://graph.microsoft.com/v1.0/users/{user_id}/onlineMeetings/{meeting_id}"

    from dataclasses import dataclass

    @dataclass
    class MSTeamsSettings:
        client_id: str
        client_secret: str
        tenant_id: str

    def __init__(self, teams_settings: Optional[MSTeamsSettings] = None):
        if teams_settings is None:
            self.client_id = settings.MS_TEAMS_CLIENT_ID
            self.client_secret = settings.MS_TEAMS_CLIENT_SECRET
            self.tenant_id = settings.MS_TEAMS_TENANT_ID
        else:
            self.client_id = teams_settings.client_id
            self.client_secret = teams_settings.client_secret
            self.tenant_id = teams_settings.tenant_id
        # Initialize MS Graph client here
        self.access_token = None

    def _get_cached_token(self) -> Optional[str]:
        return cache.get(settings.MS_TEAMS_ACCESS_TOKEN_CACHE_KEY)

    def _cache_token(self, token: str, expires_in: int) -> None:
        # Cache token for slightly less than its expiry time
        cache.set(settings.MS_TEAMS_ACCESS_TOKEN_CACHE_KEY, token, expires_in - 300)

    def _get_access_token(self) -> str:
        cached_token = self._get_cached_token()
        if cached_token:
            return cached_token

        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
        }

        response = requests.post(self.AUTH_URL, headers=headers, data=data)
        response.raise_for_status()
        token_data = response.json()
        self._cache_token(token_data["access_token"], token_data["expires_in"])
        return token_data["access_token"]

    def create_meeting(
        self,
        presenter: Presenter,
        start_time: datetime,
        end_time: datetime,
        subject: str,
    ) -> MeetingDetails:
        """
        Create a Teams meeting with the specified parameters.

        Args:
            presenter: Presenter details containing guid, name and email
            start_time: Meeting start time
            end_time: Meeting end time
            subject: Meeting subject/title

        Returns:
            MeetingDetails containing meeting id, join URL and all metadata
        """
        try:
            access_token = self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            meeting_data = {
                "startDateTime": start_time.isoformat() + "Z",
                "endDateTime": end_time.isoformat() + "Z",
                "subject": subject,
                "recordAutomatically": False,
                "lobbyBypassSettings": {"scope": "everyone"},
                "allowedPresenters": "organization",
                "participants": {
                    "organizer": {
                        "identity": {
                            "user": {
                                "id": settings.MS_TEAMS_ADMIN_USER_ID,
                                "displayName": settings.MS_TEAMS_ADMIN_USER_NAME,
                            }
                        },
                        "upn": settings.MS_TEAMS_ADMIN_UPN,
                    },
                    "attendees": [
                        {
                            "identity": {
                                "user": {
                                    "id": presenter.get('guid'),
                                    "displayName": presenter.get('name'),
                                },
                                "role": "presenter",
                                "upn": presenter.get('upn'),
                            }
                        }
                    ],
                },
            }

            response = requests.post(
                self.GRAPH_API_URL.format(user_id=presenter.get('guid')),
                headers=headers,
                json=meeting_data,
            )
            response.raise_for_status()
            meeting_details = response.json()

            return MeetingDetails(
                id=meeting_details.get("id"),
                join_url=meeting_details.get("joinWebUrl"),
                all_details=meeting_details,
            )

        except requests.exceptions.RequestException as e:
            # If authentication failed, clear cache and retry once
            if e.response and e.response.status_code == 401:
                cache.delete(settings.MS_TEAMS_ACCESS_TOKEN_CACHE_KEY)
                return self.create_meeting(presenter, start_time, end_time, subject)
            raise

    def delete_meeting(self,presenter:Presenter,meeting_id:str) -> None:
        try:
            access_token = self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            response=requests.delete(
                headers=headers,
                url=self.MEETING_ID_URL.format(user_id=presenter.get('guid'),meeting_id=meeting_id)
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # If authentication failed, clear cache and retry once
            if e.response and e.response.status_code == 401:
                cache.delete(settings.MS_TEAMS_ACCESS_TOKEN_CACHE_KEY)
                return self.delete_meeting(meeting_id=meeting_id)
            raise
            
    def update_meeting(self,presenter:Presenter,meeting_id:str,start_time: datetime,end_time: datetime,subject: str) -> None:
        try:
            access_token = self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            meeting_data = {
                "startDateTime": start_time.isoformat() + "Z",
                "endDateTime": end_time.isoformat() + "Z",
                "subject": subject
            }
            response=requests.patch(
                headers=headers,
                url=self.MEETING_ID_URL.format(user_id=presenter.get('guid'),meeting_id=meeting_id),
                json=meeting_data
            )
            response.raise_for_status()
            meeting_details = response.json()
        
            return MeetingDetails(
                id=meeting_details.get("id"),
                join_url=meeting_details.get("joinWebUrl"),
                all_details=meeting_details,
            )

        except requests.exceptions.RequestException as e:
            # If authentication failed, clear cache and retry once
            if e.response and e.response.status_code == 401:
                cache.delete(settings.MS_TEAMS_ACCESS_TOKEN_CACHE_KEY)
                return self.delete_meeting(meeting_id=meeting_id)
            raise