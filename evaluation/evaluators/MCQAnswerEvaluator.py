from evaluation.evaluators.AnswerEvaluator import AnswerEvaluator
from evaluation.models import UserEvalQuestionAttempt


class MCQAnswerEvaluator(AnswerEvaluator):

    def __init__(self, question_attempt: UserEvalQuestionAttempt):
        super().__init__(question_attempt)

    def evaluate(self):

        if self.question_attempt.status == UserEvalQuestionAttempt.Status.EVALUATED:
            return
        if self.question_attempt.question.check_is_scoring_enabled:
            eval_data = {
                "is_correct": self.question_attempt.question.question_data["answer"]
                == self.question_attempt.mcq_answer
            }
            self.question_attempt.eval_data = eval_data
        self.question_attempt.status = UserEvalQuestionAttempt.Status.EVALUATED

        self.question_attempt.save()
