from django.forms.models import model_to_dict
from typing import Dict, Any

class MeetingSerializer:
    @staticmethod
    def to_dict(meeting) -> Dict[str, Any]:
        """
        Serialize a meeting instance to a dictionary
        """
        return model_to_dict(
            meeting,
            fields=[
                'id',
                'attendance_metadata',
                'recording_metadata',
                'blob_url'
            ]
        )

    @staticmethod
    def serialize_meetings(meetings) -> list:
        """
        Serialize a list of meetings to a list of dictionaries
        """
        return [MeetingSerializer.to_dict(meeting) for meeting in meetings] 