from evaluation.evaluators.LanguageAssessmentEvaluator import LanguageAssessmentEvaluator
from evaluation.evaluators.LogicalAssessmentEvaluator import LogicalAssessmentEvaluator
from evaluation.evaluators.PersonalityAssessmentEvaluator import PersonalityAssessmentEvaluator
from evaluation.evaluators.AssessmentEvaluator import AssessmentEvaluator
from evaluation.evaluators.DSAAssessmentEvaluator import DSAAssessmentEvaluator
from evaluation.evaluators.MockInterviewBehaviouralEvaluator import MockInterviewBehaviouralEvaluator
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.models import AssessmentAttempt
import logging

logger = logging.getLogger(__name__)

class AssessmentEvaluatorProcessor(EventProcessor):
    def initialize(self):
        self.assessment_attempt_id = self.root_arguments.get("assessment_attempt_id")

    def _execute(self):
        self.initialize()
        assessment_attempt = AssessmentAttempt.objects.get(assessment_id=self.assessment_attempt_id)
        assessment_evaluator: AssessmentEvaluator = None
        
        if assessment_attempt.type == int(AssessmentAttempt.Type.LANGUAGE):
            assessment_evaluator = LanguageAssessmentEvaluator(assessment_attempt)
        elif assessment_attempt.type == int(AssessmentAttempt.Type.LOGIC):
            assessment_evaluator = LogicalAssessmentEvaluator(assessment_attempt)
        elif assessment_attempt.type == int(AssessmentAttempt.Type.PERSONALITY):            
            assessment_evaluator = PersonalityAssessmentEvaluator(assessment_attempt)
        elif assessment_attempt.type == int(AssessmentAttempt.Type.DSA_PRACTICE):
            assessment_evaluator = DSAAssessmentEvaluator(assessment_attempt)
        elif assessment_attempt.type == int(AssessmentAttempt.Type.MOCK_BEHAVIOURAL):
            assessment_evaluator = MockInterviewBehaviouralEvaluator(assessment_attempt)
        
        assessment_evaluator.evaluate()