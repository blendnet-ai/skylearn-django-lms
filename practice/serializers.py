from evaluation.models import UserAttemptResponseEvaluation
from rest_framework import serializers

from .models import UserAttemptedQuestionResponse, UserQuestionAttempt


class UserQuestionAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserQuestionAttempt
        fields = '__all__'


class UserAttemptedQuestionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAttemptedQuestionResponse
        fields = '__all__'


class ResponseReviewSerializer(serializers.ModelSerializer):

    question_text = serializers.SerializerMethodField()
    user_response = serializers.SerializerMethodField()
    ideal_response = serializers.SerializerMethodField()

    class Meta:
        model = UserAttemptResponseEvaluation
        fields = ('question_text', 'user_response', 'ideal_response')

    def get_question_text(self, obj):
        return obj.ideal_response_details.get("question_text")

    def get_user_response(self, obj):
        return obj.ideal_response_details.get("user_response")

    def get_ideal_response(self, obj):
        return obj.ideal_response_details.get("ideal_response")
