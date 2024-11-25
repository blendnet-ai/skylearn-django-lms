from datetime import datetime, timedelta
import json
from data_repo.models import QuestionBank
from evaluation.evaluators.AnswerEvaluator import AnswerEvaluator
from evaluation.event_flow.core.orchestrator import Orchestrator
from evaluation.event_flow.helpers.commons import get_eventflow_type_from_question_type
from evaluation.models import UserEvalQuestionAttempt


class EvaluationData:
    def __init__(self, id, eventflow_id) -> None:
        self.id = id
        self.eventflow_id = eventflow_id


class WritingAnswerEvaluator(AnswerEvaluator):

    def __init__(self, question_attempt: UserEvalQuestionAttempt):
        super().__init__(question_attempt)

    def evaluate(self):
        question_text = self.question_attempt.question.question_data["question"]

        eventflow_id = Orchestrator.start_new_eventflow(
            eventflow_type="writing",
            root_args={
                "text": self.question_attempt.answer_text,
                "evaluation_id": str(self.question_attempt.evaluation_id),
                "question": question_text,
                "question_attempt_id": self.question_attempt.id,
                "assessment_attempt_id": self.question_attempt.assessment_attempt_id.assessment_id,
            },
            initiated_by=self.question_attempt.user_id,
        )
        # self.question_attempt.eventflow_id = eventflow_id
        self.question_attempt.status = UserEvalQuestionAttempt.Status.EVALUATING

        self.question_attempt.save()
