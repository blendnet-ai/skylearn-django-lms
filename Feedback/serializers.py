from rest_framework import serializers

from Feedback.repositories import FeedbackFormRepository, FeedbackResponseRepository
from .models import FeedbackResponse


class FeedbackResponseSerializer(serializers.ModelSerializer):
    form_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = FeedbackResponse
        fields = ["form_id", "data"]

    def create(self, validated_data):
        form_id = validated_data.pop("form_id")
        form = FeedbackFormRepository.get(form_id)
        validated_data["form"] = form

        return FeedbackResponseRepository.create(**validated_data)
