from evaluation.models import UserEvalQuestionAttempt


class AnswerEvaluator:

    def __init__(self, question_attempt: UserEvalQuestionAttempt):
        self.question_attempt = question_attempt

    def evaluate(self):
        raise NotImplementedError
