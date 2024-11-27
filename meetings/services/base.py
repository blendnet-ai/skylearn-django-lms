from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional


@dataclass
class Presenter:
    guid: str
    name: str
    email: str


@dataclass
class MeetingDetails:
    id: str
    join_url: str
    all_details: Dict


class BaseConferencePlatformService(ABC):
    @abstractmethod
    def create_meeting(
        self,
        presenter: Presenter,
        start_time: datetime,
        end_time: datetime,
        subject: str,
    ) -> MeetingDetails:
        """
        Create a meeting in the conference platform

        Args:
            presenter: Presenter details containing guid, name and email
            start_time: Meeting start time
            end_time: Meeting end time
            subject: Meeting subject/title

        Returns:
            MeetingDetails containing meeting id, join URL and all metadata
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
