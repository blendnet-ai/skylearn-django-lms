from evaluation.models import AssessmentAttempt, Question, UserEvalQuestionAttempt


class AssessmentEvaluator:
    def __init__(self, assessment_attempt: AssessmentAttempt):
        self.assessment_attempt = assessment_attempt

    def _should_start_evaluation(self):

        if self.assessment_attempt.closed and not self.assessment_attempt.evaluation_triggered and self.assessment_attempt.status != int(AssessmentAttempt.Status.ABANDONED):

            if self.assessment_attempt.type == int(AssessmentAttempt.Type.PERSONALITY):
                return True

            count_of_unevaluated_questions = UserEvalQuestionAttempt.objects.filter(
                assessment_attempt_id=self.assessment_attempt.assessment_id
            ).exclude(                
                status__in=[UserEvalQuestionAttempt.Status.EVALUATED, UserEvalQuestionAttempt.Status.NOT_ATTEMPTED]
            ).count()
            
            if count_of_unevaluated_questions > 0:
                return False
            return True
        
        return False
    
    def evaluate(self):
        raise NotImplementedError
