from datetime import datetime, timedelta
from venv import logger
import requests
import json
import time
import jwt
from typing import Dict, Any, Optional
from django.core.cache import cache
from django.conf import settings
from .base import BaseConferencePlatformService, MeetingDetails, Presenter
from storage_service.azure_storage import AzureStorageService
import os
import subprocess
import tempfile


class ZoomConferencePlatformService(BaseConferencePlatformService):
    API_BASE_URL = "https://api.zoom.us/v2"

    from dataclasses import dataclass

    @dataclass
    class ZoomSettings:
        api_key: str
        api_secret: str
        account_id: str

    def __init__(self, zoom_settings: Optional[ZoomSettings] = None):
        if zoom_settings is None:
            self.api_key = settings.ZOOM_API_KEY
            self.api_secret = settings.ZOOM_API_SECRET
            self.account_id = settings.ZOOM_ACCOUNT_ID
        else:
            self.api_key = zoom_settings.api_key
            self.api_secret = zoom_settings.api_secret
            self.account_id = zoom_settings.account_id

    def _encode_credentials(self, client_id, client_secret):
        import base64
        credentials = f"{client_id}:{client_secret}".encode("utf-8")
        return base64.b64encode(credentials).decode("utf-8")

    def _get_cached_token(self) -> Optional[str]:
        return cache.get(settings.ZOOM_ACCESS_TOKEN_CACHE_KEY)

    def _cache_token(self, token: str, expires_in: int) -> None:
        # Cache token for slightly less than its expiry time
        cache.set(settings.ZOOM_ACCESS_TOKEN_CACHE_KEY, token, expires_in - 300)

    def _get_access_token(self) -> str:
        cached_token = self._get_cached_token()
        if cached_token:
            return cached_token

        # Zoom OAuth token endpoint
        token_url = f"https://zoom.us/oauth/token?grant_type=account_credentials&account_id={self.account_id}"

        # Client credentials (from your Zoom app)
        client_id = self.api_key
        client_secret = self.api_secret

        # Make the request for a new token
        response = requests.post(
            token_url,
            headers={
                "Authorization": f"Basic {self._encode_credentials(client_id,client_secret)}"
            },
        )

        if response.status_code != 200:
            raise Exception(f"Error fetching Zoom access token: {response.json()}")

        token_data = response.json()
        access_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)

        # Cache the token to reduce API calls (duration in seconds)
        self._cache_token(access_token, expires_in)

        return access_token

    def create_meeting(
        self,
        presenter: Presenter,
        start_time: datetime,
        end_time: datetime,
        subject: str,
    ) -> MeetingDetails:
        """
        Create a Zoom meeting with the specified parameters.

        Args:
            presenter: Presenter details containing id, name and email
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

            # Calculate duration in minutes
            duration = int((end_time - start_time).total_seconds() / 60)

            meeting_data = {
                "topic": subject,
                "type": 2,  # Scheduled meeting
                "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "duration": duration,  # in minutes
                "timezone": "Asia/Kolkata",  # Change timezone to IST
                "settings": {
                    "auto_recording": "cloud",
                    "join_before_host": True,
                    "waiting_room": False,
                    "require_password": False
                },
            }
            print(presenter)

            # Create the meeting under the presenter's user ID
            response = requests.post(
                f"{self.API_BASE_URL}/users/{presenter.get('zoom_gmail')}/meetings",
                headers=headers,
                json=meeting_data,
            )
            response.raise_for_status()
            meeting_details = response.json()

            return MeetingDetails(
                id=str(meeting_details.get("id")),
                join_url=meeting_details.get("join_url"),
                all_details=meeting_details,
            )

        except requests.exceptions.RequestException as e:
            # If authentication failed, clear cache and retry once
            if e.response and e.response.status_code == 401:
                cache.delete(settings.ZOOM_ACCESS_TOKEN_CACHE_KEY)
                return self.create_meeting(presenter, start_time, end_time, subject)
            raise

    def delete_meeting(self, presenter: Presenter, meeting_id: str) -> None:
        try:
            access_token = self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            response = requests.delete(
                f"{self.API_BASE_URL}/meetings/{meeting_id}", headers=headers
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            # If authentication failed, clear cache and retry once
            if e.response and e.response.status_code == 401:
                cache.delete(settings.ZOOM_ACCESS_TOKEN_CACHE_KEY)
                return self.delete_meeting(presenter, meeting_id)
            raise

    def update_meeting(
        self,
        presenter: Presenter,
        meeting_id: str,
        start_time: datetime,
        end_time: datetime,
        subject: str,
    ) -> MeetingDetails:
        try:
            access_token = self._get_access_token()
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Calculate duration in minutes
            duration = int((end_time - start_time).total_seconds() / 60)

            meeting_data = {
                "topic": subject,
                "start_time": start_time.strftime("%Y-%m-%dT%H:%M:%S"),
                "duration": duration,
                "timezone": "Asia/Kolkata",
            }

            response = requests.patch(
                f"{self.API_BASE_URL}/meetings/{meeting_id}",
                headers=headers,
                json=meeting_data,
            )
            response.raise_for_status()

            # Get the updated meeting details
            get_response = requests.get(
                f"{self.API_BASE_URL}/meetings/{meeting_id}", headers=headers
            )
            get_response.raise_for_status()
            meeting_details = get_response.json()

            return MeetingDetails(
                id=str(meeting_details.get("id")),
                join_url=meeting_details.get("join_url"),
                all_details=meeting_details,
            )

        except requests.exceptions.RequestException as e:
            # If authentication failed, clear cache and retry once
            if e.response and e.response.status_code == 401:
                cache.delete(settings.ZOOM_ACCESS_TOKEN_CACHE_KEY)
                return self.update_meeting(
                    presenter, meeting_id, start_time, end_time, subject
                )
            raise

    def get_meetings_recordings(self, presenter: Presenter, meeting) -> list:
        """
        Get recordings for a single Zoom meeting.

        Args:
            presenter: Presenter details
            meeting: Meeting object containing conference metadata

        Returns:
            List of recording details for the meeting
        """
        # Generate a cache key using meeting ID
        meeting_id = meeting.conference_id
        cache_key = f"zoom_recordings_{meeting_id}"

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

            # Get recordings for this specific meeting
            recordings_url = f"{self.API_BASE_URL}/meetings/{meeting_id}/recordings"

            response = requests.get(url=recordings_url, headers=headers)
            response.raise_for_status()
            recordings_data = response.json()

            # Extract recording files
            recording_files = recordings_data.get("recording_files", [])

            # Cache the recordings for 5 minutes (adjust timeout as needed)
            cache.set(cache_key, recording_files, timeout=300)

            return recording_files

        except requests.exceptions.RequestException as e:
            # If authentication failed, clear cache and retry once
            if e.response and e.response.status_code == 401:
                cache.delete(settings.ZOOM_ACCESS_TOKEN_CACHE_KEY)
                return self.get_meetings_recordings(presenter, meeting)
            raise

    def get_meeting_attendance(
        self, presenter: Presenter, meeting_id: str
    ) -> Dict[str, Any]:
        """
        Get attendance records for a Zoom meeting.

        Args:
            presenter: Presenter details
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

            # Get the meeting participants report
            participants_url = (
                f"{self.API_BASE_URL}/report/meetings/{meeting_id}/participants"
            )

            response = requests.get(url=participants_url, headers=headers)

            if response.status_code == 404:
                # Report might not be ready yet
                return None

            response.raise_for_status()

            return response.json()

        except requests.exceptions.RequestException as e:
            # If authentication failed, clear cache and retry once
            if e.response and e.response.status_code == 401:
                cache.delete(settings.ZOOM_ACCESS_TOKEN_CACHE_KEY)
                return self.get_meeting_attendance(presenter, meeting_id)
            raise

    def download_and_upload_recording(
        self, meeting_id: str, recording_metadata: list, container_name: str
    ) -> str:
        """
        Downloads a meeting recording using metadata, merges them, and uploads to Azure storage.

        Args:
            meeting_id (str): ID of the meeting.
            recording_metadata (list): List of recording metadata from Teams.
            container_name (str): Azure storage container name.

        Returns:
            str: The uploaded blob URL.
        """
        try:
            access_token = self._get_access_token()
            recording_metadata = next(
                (
                    r
                    for r in recording_metadata
                    if r.get("recording_type") == "shared_screen_with_speaker_view"
                ),
                None,
            )
            with tempfile.TemporaryDirectory() as temp_dir:
                recording_files = []

                # Fetch all recordings and save to temp files
                for index, recording_data in enumerate(recording_metadata):
                    logger.info(f"Fetching recording {index + 1}...")
                    # Get the download URL from the recording metadata
                    download_url = recording_metadata.get("download_url")

                    if not download_url:
                        raise ValueError("No download URL found in recording metadata")

                    # For Zoom, we need to append access token as query parameter
                    download_url = f"{download_url}?access_token={access_token}"

                    # Download the recording
                    response = requests.get(download_url, stream=True)
                    response.raise_for_status()
                    file_content = response.content

                    # Generate a unique filename for each recording
                    local_path = os.path.join(
                        temp_dir, f"recording_{meeting_id}_index{index}.mp4"
                    )

                    with open(local_path, "wb") as f:
                        f.write(file_content)

                    recording_files.append(local_path)

                # Create input.txt for ffmpeg
                input_file_path = os.path.join(
                    temp_dir, f"input_recording_files_{meeting_id}.txt"
                )
                with open(input_file_path, "w") as input_file:
                    for recording in recording_files:
                        input_file.write(f"file '{recording}'\n")

                # Generate unique merged output filename
                unique_output_filename = f"merged_recording_{meeting_id}.mp4"
                output_file = os.path.join(temp_dir, unique_output_filename)

                # Merge recordings using ffmpeg
                subprocess.run(
                    [
                        "ffmpeg",
                        "-f",
                        "concat",
                        "-safe",
                        "0",
                        "-i",
                        input_file_path,
                        "-c",
                        "copy",
                        output_file,
                    ],
                    check=True,
                )

                # Upload merged recording to Azure
                blob_name = f"recordings/{meeting_id}/{unique_output_filename}"
                storage_service = AzureStorageService()
                with open(output_file, "rb") as merged_file:
                    blob_url = storage_service.upload_blob(
                        container_name=container_name,
                        blob_name=blob_name,
                        content=merged_file,
                        overwrite=True,
                    )

                logger.info(f"Merged recording uploaded to: {blob_url}")

                return blob_url

        except Exception as e:
            logger.error(f"Error downloading/uploading recording: {str(e)}")
            raise
