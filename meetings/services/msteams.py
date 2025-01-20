from datetime import datetime, timedelta
from venv import logger
import requests
from typing import Dict, Any, Optional
from django.core.cache import cache
from django.conf import settings
from .base import BaseConferencePlatformService, MeetingDetails, Presenter
from storage_service.azure_storage import AzureStorageService


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
                                "id": presenter.get('guid'),
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
                return self.update_meeting(presenter,meeting_id,start_time,end_time,subject)
            raise
    
    def get_meetings_recordings(self, presenter: Presenter, meeting) -> list:
        """
        Get recordings for a single Teams meeting.
        
        Args:
            presenter: Presenter details containing guid
            meeting: Meeting object containing conference metadata
            
        Returns:
            List of recording details for the meeting
        """
        # Generate a cache key using presenter guid and meeting thread_id
        thread_id = meeting.conference_metadata.get('chatInfo', {}).get('threadId')
        cache_key = f"teams_recordings_{presenter.get('guid')}_{thread_id}"
        
        # Try to get recordings from cache
        cached_recordings = cache.get(cache_key)
        if cached_recordings is not None:
            logger.info(f"Returning cached recordings for {cache_key}")
            return cached_recordings
        
        try:
            access_token = self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            # Get all recordings from user's OneDrive recordings folder
            recordings_url = f"https://graph.microsoft.com/v1.0/users/{presenter.get('guid')}/drive/root:/Recordings:/children"
            
            response = requests.get(
                url=recordings_url,
                headers=headers
            )
            response.raise_for_status()
            recordings_data = response.json()
            
            # Filter recordings for this specific meeting
            meeting_recordings = []
            
            for recording in recordings_data.get('value', []):
                if recording.get('source', {}).get('threadId') == thread_id:
                    meeting_recordings.append(recording)
            
            # Cache the recordings for 5 minutes (adjust timeout as needed)
            cache.set(cache_key, meeting_recordings, timeout=300)
            
            return meeting_recordings

        except requests.exceptions.RequestException as e:
            # If authentication failed, clear cache and retry once
            if e.response and e.response.status_code == 401:
                cache.delete(settings.MS_TEAMS_ACCESS_TOKEN_CACHE_KEY)
                return self.get_meetings_recordings(presenter, meeting)  # Fixed parameter name
            raise
        

    def get_meeting_attendance(self, presenter: Presenter, meeting_id: str) -> Dict[str, Any]:
        """
        Get attendance records for a Teams meeting.
        
        Args:
            presenter: Presenter details containing guid
            meeting_id: The ID of the meeting to get attendance for
            
        Returns:
            Dict containing attendance records and metadata
        """
        try:
            access_token = self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            
            # First get the attendance reports
            reports_url = f"https://graph.microsoft.com/v1.0/users/{presenter.get('guid')}/onlineMeetings/{meeting_id}/attendanceReports"
            response = requests.get(
                url=reports_url,
                headers=headers
            )
            response.raise_for_status()
            
            attendance_reports = response.json().get('value', [])
            if not attendance_reports or len(attendance_reports) == 0:
                return None
            
            # Get the details of the most recent report
            latest_report = attendance_reports[0]
            report_id = latest_report['id']
            
            # Get the detailed attendance records
            attendance_url = f"{reports_url}/{report_id}/attendanceRecords"
            attendance_response = requests.get(
                url=attendance_url,
                headers=headers
            )
            attendance_response.raise_for_status()
            
            return attendance_response.json()

        except requests.exceptions.RequestException as e:
            # If authentication failed, clear cache and retry once
            if e.response and e.response.status_code == 401:
                cache.delete(settings.MS_TEAMS_ACCESS_TOKEN_CACHE_KEY)
                return self.get_meeting_attendance(presenter, meeting_id)
            raise

    def download_and_upload_recording(self, meeting_id: str, recording_metadata: dict, container_name: str) -> str:
        """
        Downloads a meeting recording using metadata and uploads to Azure storage.
        First tries the download URL from metadata, falls back to generating new URL if needed.
        
        Args:
            recording_metadata (dict): Recording metadata from Teams
            container_name (str): Azure storage container name
            
        Returns:
            str: The uploaded blob URL
        """
        try:
            # First try using the download URL from metadata
            download_url = recording_metadata.get("@microsoft.graph.downloadUrl")
            if download_url:
                try:
                    response = requests.get(download_url, stream=True)
                    response.raise_for_status()
                    # If successful, proceed with this content
                    file_content = response.content
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 401 or e.response.status_code == 403:  # Forbidden/expired URL
                        logger.info("Download URL expired, generating new one")
                        file_content = self.download_meeting_recording_using_graph_api(recording_metadata)
                    else:
                        raise
            else:
                # If no download URL in metadata, use Graph API
                file_content = self.download_meeting_recording_using_graph_api(recording_metadata)

            # Generate blob name with timestamp
            file_name = recording_metadata["name"]
            blob_name = f"recordings/{meeting_id}_{file_name}"
            
            # Upload to Azure storage
            storage_service = AzureStorageService()
            blob_url = storage_service.upload_blob(
                container_name=container_name,
                blob_name=blob_name,
                content=file_content,
                overwrite=True
            )
            
            
            return blob_url
            
        except Exception as e:
            logger.error(f"Error downloading/uploading recording: {str(e)}")
            raise

    def download_meeting_recording_using_graph_api(self, recording_metadata: dict) -> bytes:
        """
        Downloads recording using Graph API as fallback method
        """
        access_token = self._get_access_token()
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        file_id = recording_metadata["id"]
        drive_id = recording_metadata["parentReference"]["driveId"]
        graph_api_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/content"
        
        response = requests.get(graph_api_url, headers=headers, stream=True)
        response.raise_for_status()
        
        return response.content

