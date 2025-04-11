from django.forms.models import model_to_dict
from typing import Dict, Any
from rest_framework import serializers


class MeetingSerializer:
    @staticmethod
    def to_dict(meeting) -> Dict[str, Any]:
        """
        Serialize a meeting instance to a dictionary
        """
        return model_to_dict(
            meeting,
            fields=["id", "attendance_metadata", "recording_metadata", "blob_url"],
        )

    @staticmethod
    def serialize_meetings(meetings) -> list:
        """
        Serialize a list of meetings to a list of dictionaries
        """
        return [MeetingSerializer.to_dict(meeting) for meeting in meetings]


class AdditionalRecordingSerializer(serializers.Serializer):
    file = serializers.FileField()
    filename = serializers.CharField(max_length=255)

    def validate_file(self, value):
        """Validate file is a video"""
        valid_types = ["video/mp4", "video/quicktime", "video/x-msvideo"]
        if value.content_type not in valid_types:
            raise serializers.ValidationError(
                "Only video files (mp4, mov, avi) are allowed"
            )
        return value
