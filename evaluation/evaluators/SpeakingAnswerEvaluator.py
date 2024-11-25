from datetime import datetime, timedelta
import json
from data_repo.models import QuestionBank
from evaluation.evaluators.AnswerEvaluator import AnswerEvaluator
from evaluation.event_flow.core.orchestrator import Orchestrator
from evaluation.event_flow.helpers.commons import get_eventflow_type_from_question_type
from evaluation.models import UserEvalQuestionAttempt, Question
from config.celery import app
import uuid


class EvaluationData:
    def __init__(self, id, eventflow_id) -> None:
        self.id = id
        self.eventflow_id = eventflow_id


class SpeakingAnswerEvaluator(AnswerEvaluator):

    def __init__(self, question_attempt: UserEvalQuestionAttempt):
        super().__init__(question_attempt)

    def evaluate(self):
        question_text = self.question_attempt.question.question_data["question"]
        type_of_flow = type_of_flow = "mock_behavioural" if self.question_attempt.question.category == int(Question.Category.MOCK_BEHAVIOURAL) else "speaking"
        dt_append = datetime.now().strftime("%d|%m-%H:%M")
        eventflow_id = Orchestrator.start_new_eventflow(
            eventflow_type=type_of_flow,
            root_args={
                "audio_blob_path": self.question_attempt.audio_path,
                "converted_audio_blob_path": self.question_attempt.converted_audio_path,
                "base_storage_path": f"base_storage/{dt_append}",
                "storage_container_name": "speaking-audios",
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
