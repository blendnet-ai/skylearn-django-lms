from datetime import datetime, timedelta
import json
from data_repo.models import QuestionBank
from evaluation.evaluators.AnswerEvaluator import AnswerEvaluator
from evaluation.event_flow.core.orchestrator import Orchestrator
from evaluation.event_flow.helpers.commons import get_eventflow_type_from_question_type
from evaluation.models import UserEvalQuestionAttempt,AssessmentAttempt
from config.celery import app
import uuid
from ai_learning.repositories import DSAPracticeChatDataRepository
from evaluation.repositories import AssessmentAttemptRepository
class EvaluationData:
    def __init__(self, id, eventflow_id) -> None:
        self.id = id
        self.eventflow_id = eventflow_id


class DSAPracticeEvaluator(AnswerEvaluator):
    def __init__(self, question_attempt: UserEvalQuestionAttempt):
        super().__init__(question_attempt)

    def evaluate(self):
        question_text = self.question_attempt.question.question_data["question"]
        attempt = AssessmentAttemptRepository.fetch_assessment_attempt(
            assessment_id=self.question_attempt.assessment_attempt_id.assessment_id
        )
        test_cases_score = attempt.eval_data.get('code_correctness_score', {})
        dsa_practice_chat_data = DSAPracticeChatDataRepository.get_chat_session_history(
            user_id=self.question_attempt.user_id.id,
            question_id=self.question_attempt.question.id,
            assessment_attempt_id=self.question_attempt.assessment_attempt_id.assessment_id
        )

        if test_cases_score.get('code_correctness_score', 0) < 10:
            # Mark as evaluated if score is less than 10
            self.question_attempt.status = UserEvalQuestionAttempt.Status.EVALUATED
            self.question_attempt.save()
            attempt.status = AssessmentAttempt.Status.COMPLETED
            attempt.evaluation_triggered = True
            attempt.save()
        else:
            # Retrieve chat history if data exists, else set to an empty list
            chat_history = dsa_practice_chat_data if dsa_practice_chat_data else []
            
            # Append current date and time to event flow
            dt_append = datetime.now().strftime("%d|%m-%H:%M")
            
            # Start a new event flow
            eventflow_id = Orchestrator.start_new_eventflow(
                eventflow_type="coding",
                root_args={
                    "evaluation_id": str(self.question_attempt.evaluation_id),
                    "question": question_text,
                    "solution": self.question_attempt.code,
                    "chat_history": chat_history,
                    "question_attempt_id": self.question_attempt.id,
                    "test_cases_score": test_cases_score,
                    "assessment_attempt_id": self.question_attempt.assessment_attempt_id.assessment_id,
                },
                initiated_by=self.question_attempt.user_id,
            )
            
            # Update question attempt status to evaluating
            self.question_attempt.status = UserEvalQuestionAttempt.Status.EVALUATING
            self.question_attempt.save()

