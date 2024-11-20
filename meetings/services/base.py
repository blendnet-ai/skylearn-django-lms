from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Optional


class BaseConferencePlatformService(ABC):
    @abstractmethod
    def create_meeting(
        self,
        presenter: Dict[str, str],
        start_time: datetime,
        end_time: datetime,
        subject: str,
    ) -> Dict[str, str]:
        """
        Create a meeting in the conference platform

        Args:
            presenter: Dict containing presenter details (guid, name, email)
            start_time: Meeting start time
            end_time: Meeting end time
            subject: Meeting subject/title

        Returns:
            Dict containing meeting metadata and ID
        """
        pass

    @abstractmethod
    def delete_meeting(self, meeting_id: str) -> None:
        """
        Delete a meeting from the conference platform

        Args:
            meeting_id: ID of meeting to delete
        """
        pass
