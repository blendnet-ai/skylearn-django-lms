from rest_framework import serializers

from .models import UserAttemptResponseEvaluation, QuestionIssues


class UserAttemptResponseEvaluationSerializer(serializers.ModelSerializer):
    status_text = serializers.ReadOnlyField(source='status_string')
    class Meta:
        model = UserAttemptResponseEvaluation
        fields = '__all__'

class DSABotRequestSerializer(serializers.Serializer):
    message = serializers.CharField()
    question_id = serializers.IntegerField()
    assessment_id = serializers.IntegerField()
    token = serializers.CharField()
    code = serializers.CharField()
    language = serializers.CharField()
    run_result = serializers.JSONField()

class DSAChatHistoryQueryParamsSerializer(serializers.Serializer):
    assessment_id = serializers.IntegerField(required=True)
    question_id = serializers.IntegerField(required=True)

class QuestionIssuesSerializer(serializers.Serializer):
    question_id=serializers.IntegerField(required=True)
    assessment_attempt_id=serializers.IntegerField(required=True)
    type_of_issue = serializers.ChoiceField(choices=QuestionIssues.TypeOfIssue.choices, required=True)
    description=serializers.CharField(required=True)
