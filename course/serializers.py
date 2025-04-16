from datetime import timedelta
from rest_framework import serializers

from course.models import Batch, Course, Module, Upload, UploadVideo
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

    def validate_batch_ids(self, value):
        if len(value) > 1:
            raise serializers.ValidationError(
                "You can create live class series for only one batch at a time"
            )
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


class BatchSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    lecturer_id = serializers.IntegerField()
    start_date = serializers.DateField(required=False, allow_null=True)
    end_date = serializers.DateField(required=False, allow_null=True)


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
        child=serializers.IntegerField(), required=False
    )


class BulkEnrollmentSerializer(serializers.Serializer):
    file = serializers.FileField(
        required=True,
        allow_empty_file=False,
        help_text="Upload Excel file containing student enrollment data",
    )

    def validate_file(self, value):
        if not value.name.endswith(".xlsx"):
            raise serializers.ValidationError("Only Excel (.xlsx) files are supported")
        if value.size > 5242880:  # 5MB limit
            raise serializers.ValidationError("File size cannot exceed 5MB")
        return value


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ["id", "title", "code", "summary", "course_hours"]
        read_only_fields = ["id"]

    def validate_duration(self, value):
        if value <= 0:
            raise serializers.ValidationError("Duration must be greater than 0")
        return value


class ModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Module
        fields = ["id", "title", "order_in_course"]
        read_only_fields = ["id"]

    def validate_order_in_course(self, value):
        if value < 1:
            raise serializers.ValidationError("Module order must be greater than 0")
        return value


class UploadMaterialSerializer(serializers.ModelSerializer):
    file_type = serializers.ChoiceField(choices=["reading", "video"])
    course = serializers.PrimaryKeyRelatedField(queryset=Course.objects.all())
    module = serializers.PrimaryKeyRelatedField(queryset=Module.objects.all())

    class Meta:
        model = Upload  # or whichever model you're using
        fields = ["title", "course", "module", "file_type"]

    def validate_file_type(self, value):
        """
        Validate file_type is either 'reading' or 'video'
        """
        if value not in ["reading", "video"]:
            raise serializers.ValidationError(
                "File type must be either 'reading' or 'video'"
            )
        return value


class DeleteMaterialTypeSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["reading", "video"])


class AssessmentConfigSerializer(serializers.Serializer):
    name = serializers.CharField()
    module_id = serializers.IntegerField()
    duration = serializers.IntegerField(help_text="Duration in minutes")
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    question_counts = serializers.DictField(
        child=serializers.IntegerField(min_value=0),
        help_text="Dict of question types and counts",
    )


class QuestionUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    question_type = serializers.ChoiceField(
        choices=["objective", "reading", "writing", "speaking", "listening"]
    )

    def validate_file(self, value):
        if not value.name.endswith(".xlsx") and not value.name.endswith(".csv"):
            raise serializers.ValidationError(
                "Only Excel (.xlsx) and CSV (.csv) files are supported"
            )
        if value.size > 5242880:  # 5MB limit
            raise serializers.ValidationError("File size cannot exceed 5MB")
        return value


class AssessmentConfigUpdateSerializer(serializers.Serializer):
    start_date = serializers.DateTimeField()
    end_date = serializers.DateTimeField()
    due_date = serializers.DateTimeField(required=False, allow_null=True)
    duration = serializers.IntegerField(
        required=False, min_value=1, help_text="Duration in minutes"
    )

    def validate(self, data):
        """Validate dates and duration"""
        if data["end_date"] <= data["start_date"]:
            raise serializers.ValidationError("End date must be after start date")

        if data.get("due_date") and data["due_date"] < data["end_date"]:
            raise serializers.ValidationError("Due date must be after end date")

        return data
