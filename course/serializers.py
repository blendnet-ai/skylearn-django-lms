from datetime import timedelta
from rest_framework import serializers

from course.models import Batch
from meetings.models import Meeting, MeetingSeries


class LiveClassSeriesSerializer(serializers.ModelSerializer):
    batch_ids = serializers.ListField(write_only=True)  # Custom field

    class Meta:
        model = MeetingSeries
        fields = [
            "title",
            "batch_ids",
            "start_time",
            "duration",
            "start_date",
            "end_date",
            "recurrence_type",
            "weekday_schedule",
            "monthly_day",
        ]
    def validate_batch_ids(self,value):
        if len(value) >1:
            raise serializers.ValidationError("You can create live class series for only one batch at a time")
        return value
        
    def validate_duration(self, value):
        """
        Validate that duration is positive and reasonable
        """
        if value <= timedelta(minutes=0):
            raise serializers.ValidationError("Duration must be atleast 1 minute")
        return value

    def validate_recurrence_type(self, value):
        """
        Validate recurrence type is one of the allowed values
        """
        allowed_types = dict(MeetingSeries.RECURRENCE_CHOICES).keys()
        if value.lower() not in allowed_types:
            raise serializers.ValidationError(
                f"Recurrence type must be one of: {', '.join(allowed_types)}"
            )
        return value.lower()


class LiveClassUpdateSerializer(serializers.ModelSerializer):
    start_time = serializers.TimeField()
    duration = serializers.DurationField()
    start_date = serializers.DateField()

    class Meta:
        model = Meeting
        fields = ["start_time", "duration", "start_date"]


class BatchSerializer(serializers.ModelSerializer):
    lecturer_id = serializers.IntegerField()

    class Meta:
        model = Batch
        fields = ["title", "lecturer_id"]


class LiveClassDateRangeSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()


class CourseMessageSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    batch_id = serializers.IntegerField()
    message = serializers.CharField()
    subject = serializers.CharField()
    
class PersonalMessageSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    message = serializers.CharField()


class BatchWithStudentsSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    lecturer_id = serializers.IntegerField()
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    student_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False
    )
