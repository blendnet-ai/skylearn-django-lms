import json

from django.core.cache import cache
from django.conf import settings

from evaluation.evaluators.AssessmentEvaluator import AssessmentEvaluator
from evaluation.models import AssessmentAttempt, Question, UserEvalQuestionAttempt
from evaluation.repositories import UserEvalQuestionAttemptRepository

class DSAAssessmentEvaluator(AssessmentEvaluator):    
    def __init__(self, assessment_attempt: AssessmentAttempt):
        self.assessment_attempt = assessment_attempt

    def evaluate(self):
        if not self._should_start_evaluation():
            return
        
        self.assessment_attempt.status = AssessmentAttempt.Status.COMPLETED

        self.assessment_attempt.evaluation_triggered = True

        self.assessment_attempt.save()

        cache.set(
            f"{self.assessment_attempt.user_id.id}{settings.LATEST_COMPLETED_ASSESSMENT_ID_CACHE_KEY_SUFFIX}",
            self.assessment_attempt.assessment_id,timeout=60*60*24*14
        )
