from rest_framework import serializers

from Feedback.repositories import FeedbackFormRepository, FeedbackResponseRepository, CourseFormEntryRepository
from .models import FeedbackResponse


class FeedbackResponseSerializer(serializers.ModelSerializer):
    course_feedback_entry_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = FeedbackResponse
        fields = ["data","course_feedback_entry_id"]

    def create(self, validated_data):
        form_id = validated_data.pop("course_feedback_entry_id")
        validated_data["course_feedback_entry"] = CourseFormEntryRepository.get(form_id)

        return FeedbackResponseRepository.create(**validated_data)
