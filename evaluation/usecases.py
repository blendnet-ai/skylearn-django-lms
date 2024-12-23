import typing
from json import JSONDecodeError
from string import Template

from rest_framework.exceptions import ValidationError

from OpenAIService.repositories import (
    LLMCommunicationWrapper,
    ValidPromptTemplates,
    ChatHistoryRepository,
)
from ai_learning.repositories import (
    DSAPracticeChatDataRepository,
    PromptTemplateRepository,
    CompileDurationLog,
)
from data_repo.repositories import ConfigMapRepository
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService
from .models import AssessmentAttempt, UserEvalQuestionAttempt, Question
from evaluation.repositories import (
    AssessmentAttemptRepository,
    AssessmentGenerationConfigRepository,
    QuestionRepository,
    UserEvalQuestionAttemptRepository,
    AudioURLProvider,
    QuestionIssuesRepository,
    DSASheetConfigRepository,
)

# from InstituteConfiguration.repositories import InstituteRepository, QuestionListRepository, DSASessionRepository
from storage_service.azure_storage import AzureStorageService
from datetime import datetime, timedelta, date, time
from evaluation.evaluators.LanguageAssessmentEvaluator import (
    LanguageAssessmentEvaluator,
)
from evaluation.evaluators.LogicalAssessmentEvaluator import LogicalAssessmentEvaluator
from evaluation.evaluators.PersonalityAssessmentEvaluator import (
    PersonalityAssessmentEvaluator,
)
from evaluation.evaluators.AssessmentEvaluator import AssessmentEvaluator
from evaluation.evaluators.DSAPracticeExecutor import DSAPracticeExecutor
from evaluation.evaluators.DSAAssessmentEvaluator import DSAAssessmentEvaluator
from evaluation.evaluators.MockInterviewBehaviouralEvaluator import (
    MockInterviewBehaviouralEvaluator,
)
from evaluation.evaluators.LSRWEvaluator import LSRWAssessmentEvaluator
from .tasks import mark_test_abandoned
from custom_auth.repositories import UserProfileRepository

# from stats.repositories import LeaderboardRepository

from django.utils import timezone
from django.conf import settings
from .models import UserEvalQuestionAttempt, AssessmentAttempt
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Union
import logging
import os
import json
import requests
import base64
import hashlib
import hmac
import openai
from random import sample

from evaluation.event_flow.services.base_rest_service import BaseRestService

logger = logging.getLogger(__name__)

evaluator_mapping = {
    "mcq_answer": "MCQAnswerEvaluator",
    "multiple_mcq_answer": "MultipleMCQAnswerEvaluator",
    "answer_text": "WritingAnswerEvaluator",
    "voice": "SpeakingAnswerEvaluator",
    "code": "DSAPracticeEvaluator",
}
import importlib


class AssessmentExpiredException(Exception):
    pass


@dataclass
class SectionWiseQuestions:
    section: Union[str, int]
    questions: List[int] = field(default_factory=list)
    skippable: bool = False

    def __post_init__(self):
        self.validate_data()

    def validate_data(self):
        if not isinstance(self.section, (str, int)):
            raise ValueError("Section must be a non-empty string.")
        if not all(isinstance(q_id, int) for q_id in self.questions):
            raise ValueError("All question IDs must be integers.")
        if not self.questions:
            raise ValueError("Questions list cannot be empty.")
        if not isinstance(self.skippable, bool):
            raise ValueError("Skippable must be a boolean.")

    def to_dict(self):
        return asdict(self)


@dataclass
class QuestionsData:
    total_number: int = 0
    category: int = ""
    questions: List[SectionWiseQuestions] = field(default_factory=list)

    def __post_init__(self):
        self.validate_data()

    def validate_data(self):
        if not isinstance(self.total_number, int) or self.total_number <= 0:
            raise ValueError("Total number must be a positive integer.")
        if not isinstance(self.category, int) or self.category is None:
            raise ValueError("Category must be a non-empty integer.")
        if not all(isinstance(scq, SectionWiseQuestions) for scq in self.questions):
            raise ValueError(
                "All section wise questions must be instances of SectionWiseQuestions."
            )
        if not self.questions:
            raise ValueError("section wise questions list cannot be empty.")

    def to_dict(self):
        return asdict(self)


@dataclass
class DSAQuestionsResponse:
    dsa_sheet_names: list
    questions: list
    topics: list
    companies: set


class AssessmentUseCase:

    def fetch_resume_storage_saas_url(user_id, file_name):
        if file_name:
            blob_name = f"{user_id}/{file_name}"
        else:
            blob_name = f"{user_id}/{os.urandom(8).hex()}"
        container_name = settings.RESUME_STORAGE_CONTAINER_NAME
        return AssessmentUseCase.fetch_azure_storage_url(blob_name, container_name)

    def fetch_azure_storage_url(blob_name, container_name):
        az_storage_service = AzureStorageService()
        return az_storage_service.generate_blob_access_url(
            container_name=container_name,
            blob_name=blob_name,
            expiry_time=datetime.now() + timedelta(days=1),
            allow_read=True,
            allow_write=True,
        )

    def fetch_display_data(user_id):
        available_assessments = AssessmentAttemptRepository.fetch_assessment_configs()
        resp_data = []
        for assessment in available_assessments:
            assessment_generation_id = assessment.assessment_generation_id

            # if (
            #     assessment_generation_id == int(AssessmentAttempt.Type.CODING) + 1
            #     and str(user_id) not in settings.USER_IDS_CODING_TEST_ENABLED
            # ):
            #     continue

            display_data = assessment.display_data
            name = assessment.assessment_display_name
            max_attempts = assessment.number_of_attempts
            start_date=assessment.start_date
            end_date=assessment.end_date
            due_date=assessment.due_date
            number_of_attempts = AssessmentAttemptRepository.number_of_attempts_expired(
                assessment_generation_config_id=assessment_generation_id,
                user_id=user_id,
            )
            
            # Check if the assessment should be locked
            current_date = timezone.now()
            if start_date is not None and end_date is not None:
                is_locked = not (start_date <= current_date <= end_date)
            else:
                is_locked = False
            
            resp_obj = {
                "assessment_generation_id": assessment_generation_id,
                "test": {
                    "heading": f"{name} test",
                    "path": f"assessment",
                    "query_params": f"?id={assessment_generation_id}",
                },
                "welcome": {
                    "heading": f"Welcome to {name} test",
                    "heading_inner": f"Welcome to your {name} test",
                    "instructions": display_data.get("instructions"),
                    "img_url": display_data.get("welcome_img_url"),
                },
                "eval_home": {
                    "heading": f"{name}",
                    "img_url": display_data.get("eval_img_url"),
                },
                "name": assessment.assessment_name,
                "max_attempts": max_attempts,
                "user_attempts": number_of_attempts,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "due_date":due_date,
                "is_locked": is_locked
 
                
            }

            resp_data.append(resp_obj)
        return resp_data

    def fetch_attempts_data(user_id):
        available_assessment_configs = (
            AssessmentAttemptRepository.fetch_assessment_configs()
        )
        current_assessments = AssessmentAttemptRepository.fetch_all_assessment_attempt(
            user_id
        )

        resp_data = []
        for assessment_config in available_assessment_configs:
            assessment_generation_id = assessment_config.assessment_generation_id
            assessment_display_name = assessment_config.assessment_display_name
            if (
                assessment_generation_id == int(AssessmentAttempt.Type.CODING) + 1
                and str(user_id) not in settings.USER_IDS_CODING_TEST_ENABLED
            ):
                continue

            assessment_attempts = (
                current_assessments.filter(
                    type=assessment_config.kwargs.get("category")
                )
                .order_by("-created_at")
                .all()
            )

            status = AssessmentAttempt.Status.CREATION_PENDING.label
            eval_data = None

            number_of_attempts = AssessmentAttemptRepository.number_of_attempts_expired(
                assessment_generation_config_id=assessment_config.assessment_generation_id,
                user_id=user_id,
            )
            latest_time = None
            assessment_attempt_id = None
            percentage = None
            short_description = None
            max_attempts = assessment_config.number_of_attempts
            if assessment_attempts:
                latest_attempt_status = assessment_attempts[0].status
                latest_time = assessment_attempts[0].start_time
                assessment_attempt_id = assessment_attempts[0].assessment_id
                if latest_attempt_status == int(AssessmentAttempt.Status.IN_PROGRESS):
                    status = AssessmentAttempt.Status.IN_PROGRESS.label

                if assessment_attempts[0].closed:
                    if (
                        latest_attempt_status == int(AssessmentAttempt.Status.COMPLETED)
                        and assessment_attempts[0].evaluation_triggered
                    ):
                        status = AssessmentAttempt.Status.COMPLETED.label
                        eval_data = assessment_attempts[0].eval_data
                    else:
                        status = AssessmentAttempt.Status.EVALUATION_PENDING.label
            if eval_data:
                percentage = eval_data.get("percentage")
                short_description = eval_data.get("short_description")
            resp_data.append(
                {
                    "assessment_generation_id": assessment_generation_id,
                    "assessment_display_name": assessment_display_name,
                    "name": assessment_config.assessment_name,
                    "assessment_attempt_id": assessment_attempt_id,
                    "status": status,
                    "number_of_attempts": number_of_attempts,
                    "max_attempts": max_attempts,
                    "last_attempted": latest_time,
                    "eval_data": eval_data,
                    "img_url": assessment_config.display_data.get("eval_img_url"),
                    "percentage": percentage,
                    "short_description": short_description,
                }
            )

        return resp_data

    def fetch_question_data(question_id, assessment, user, for_exeution=False):
        question = Question.objects.filter(id=question_id).first()
        resp_question_data = {
            "question_id": question.id,
            "answer_type": question.answer_type,
        }

        if question.audio_url:
            resp_question_data["audio_url"] = question.audio_url

        if question.question_data.get("questions"):
            questions = []
            for q in question.question_data.get("questions"):
                questions.append(
                    {
                        "question": q.get("question"),
                        "options": q.get("options"),
                    }
                )
            resp_question_data["questions"] = questions

        if question.question_data.get("paragraph"):
            resp_question_data["paragraph"] = question.question_data.get("paragraph")

        if question.question_data.get("question"):
            resp_question_data["question"] = question.question_data.get("question")

        if question.question_data.get("options"):
            resp_question_data["options"] = question.question_data.get("options")

        if question.question_data.get("hint"):
            resp_question_data["hint"] = question.question_data.get("hint")

        if question.question_data.get("image_url"):
            resp_question_data["image_url"] = question.question_data.get("image_url")

        if question.question_data.get("hints"):
            resp_question_data["hints"] = question.question_data.get("hints")

        if question.question_data.get("titleSlug"):
            resp_question_data["titleSlug"] = question.question_data.get("titleSlug")

        if question.question_data.get("questionTitle"):
            resp_question_data["questionTitle"] = question.question_data.get(
                "questionTitle"
            )

        if question.question_data.get("difficulty"):
            resp_question_data["difficulty"] = question.question_data.get("difficulty")
            difficulty = question.question_data.get("difficulty").lower()
            if difficulty == "basic":
                resp_question_data["expected_time"] = 20
            elif difficulty == "easy":
                resp_question_data["expected_time"] = 30
            elif difficulty == "medium":
                resp_question_data["expected_time"] = 45
            elif difficulty == "hard":
                resp_question_data["expected_time"] = 60

        if question.question_data.get("exampleTestcases"):
            resp_question_data["exampleTestcases"] = question.question_data.get(
                "exampleTestcases"
            )

        if question.question_data.get("additionalTestcases") and for_exeution:
            resp_question_data["additionalTestcases"] = question.question_data.get(
                "additionalTestcases"
            )

        if question.question_data.get("driver_codes") and for_exeution:
            resp_question_data["driver_codes"] = question.question_data.get(
                "driver_codes"
            )

        if question.tags:
            resp_question_data["topics"] = question.tags

        if question.question_data.get("companies"):
            resp_question_data["companies"] = question.question_data.get("companies")

        if question.answer_type == int(Question.AnswerType.VOICE.value):
            answer_audio_url = EvaluationUseCase.save_audio_url_speaking(
                user, question_id, assessment
            )
            resp_question_data["answer_audio_url"] = answer_audio_url

        resp_question_data["assessment_mode"] = assessment.mode

        return resp_question_data

    def assert_assessment_validity(start_time, test_duration, status):
        if not start_time:
            return
        expiration_time = start_time + test_duration
        buffer_duration_minutes = int(os.getenv("BUFFER_DURATION_MINUTES", 2))
        buffer_duration = timedelta(minutes=buffer_duration_minutes)

        if (
            status == int(AssessmentAttempt.Status.ABANDONED)
            or status == int(AssessmentAttempt.Status.COMPLETED)
            or status == int(AssessmentAttempt.Status.EVALUATION_PENDING)
        ):
            raise AssessmentExpiredException("Test has been abandoned or completed")
        if timezone.now() > expiration_time + buffer_duration:
            raise AssessmentExpiredException("Test time has expired")

    def fetch_assessment_data(assessment_id, user_id):
        assessment_details = AssessmentAttemptRepository.get_assessment_data(
            assessment_id=assessment_id, user_id=user_id
        )
        if not assessment_details:
            raise ValidationError("Assessment not found")

        return assessment_details

    def fetch_assessment_data_and_assert_validity(assessment_id, user_id):
        assessment_details = AssessmentUseCase.fetch_assessment_data(
            assessment_id=assessment_id, user_id=user_id
        )
        AssessmentUseCase.assert_assessment_validity(
            assessment_details.start_time,
            assessment_details.test_duration,
            assessment_details.status,
        )

        return assessment_details

    def fetch_next_question_id(assessment_id, user_id):
        assessment_details = (
            AssessmentUseCase.fetch_assessment_data_and_assert_validity(
                assessment_id, user_id
            )
        )

        if assessment_details:
            last_saved = (
                int(assessment_details.last_saved)
                if assessment_details.last_saved
                else None
            )
            question_list = assessment_details.question_list
            last_saved_section = (
                int(assessment_details.last_saved_section)
                if assessment_details.last_saved_section
                else None
            )

            next_question = None
            if last_saved_section is not None:
                for item in question_list:
                    if item.get("section") == last_saved_section:
                        if last_saved in item.get("questions"):
                            index_of_last_saved = item.get("questions").index(
                                last_saved
                            )
                            if index_of_last_saved + 1 < len(item.get("questions")):
                                next_question = item.get("questions")[
                                    index_of_last_saved + 1
                                ]
                                break
                            else:
                                index_of_last_saved_section = question_list.index(item)

                                if index_of_last_saved_section + 1 < len(question_list):
                                    next_question = question_list[
                                        index_of_last_saved_section + 1
                                    ].get("questions")[0]
                                    break
                                else:
                                    next_question = 0
                                    break
            elif last_saved in question_list:
                index_of_last_saved = question_list.index(last_saved)
                if index_of_last_saved + 1 < len(question_list):
                    next_question = assessment_details.question_list[
                        assessment_details.question_list.index(last_saved) + 1
                    ]
                else:
                    next_question = 0
            else:
                if isinstance(question_list, list) and all(
                    isinstance(item, dict) for item in question_list
                ):
                    next_question = question_list[0].get("questions")[0]
                else:
                    next_question = question_list[0]

        return next_question

    def fetch_question_ids_from_tag(
        category, total_questions_count, tags, section_name, skippable
    ):

        selected_question_ids = []
        questions_injestion_left = total_questions_count
        for item in tags:
            tag = item.get("tag")
            num_questions = item.get("number")
            questions = QuestionRepository.return_questions_by_tag(
                category, num_questions, tag, selected_question_ids
            )
            selected_question_ids.extend([question.id for question in questions])
            questions_injestion_left -= len(questions)

        if questions_injestion_left > 0:
            remaining_questions = QuestionRepository.return_questions_by_category(
                category, questions_injestion_left, selected_question_ids
            )
            selected_question_ids.extend(
                [question.id for question in remaining_questions]
            )

        questions_data = QuestionsData(
            total_number=total_questions_count,
            category=category,
            questions=[
                SectionWiseQuestions(
                    section=section_name,
                    questions=selected_question_ids,
                    skippable=skippable,
                )
            ],
        )

        return questions_data.to_dict()

    def fetch_question_ids_from_sub_category(
        category, total_questions_count, subcategories
    ):

        selected_question_ids = []
        sub_category_wise_questions = []

        for item in subcategories:
            sub_category = item.get("sub_category")
            num_questions = item.get("number")
            skippable = item.get("skippable")
            section_name = item.get("section_name")
            questions = QuestionRepository.return_questions_by_sub_category(
                category, sub_category, num_questions, selected_question_ids
            )
            selected_question_ids.extend([question.id for question in questions])

            # fetching existing section if there is same section name else create new section
            existing_section = next(
                (
                    section
                    for section in sub_category_wise_questions
                    if section.section == section_name
                ),
                None,
            )

            if existing_section:
                existing_section.questions.extend(
                    [question.id for question in questions]
                )
            else:
                ques_dict = SectionWiseQuestions(
                    section=section_name,
                    skippable=skippable,
                    questions=[question.id for question in questions],
                )
                sub_category_wise_questions.append(ques_dict)

        questions_data = QuestionsData(
            total_number=total_questions_count,
            category=category,
            questions=sub_category_wise_questions,
        )
        return questions_data.to_dict()

    def check_if_question_exists_in_assessment(assessment_id, question_id, user_id):
        assessment = AssessmentUseCase.fetch_assessment_data_and_assert_validity(
            assessment_id, user_id
        )
        if assessment:
            for item in assessment.question_list:
                if question_id in item.get("questions"):
                    return True
        return False

    def create_new_assessment(
        assessment_generation_id, user, assessment_generation_details
    ):

        assessment_generation_class_data = AssessmentGenerationConfigRepository.return_assessment_generation_class_data(
            assessment_generation_id
        )
        kwargs = assessment_generation_class_data.kwargs
        class_name = assessment_generation_class_data.assessment_generation_class_name
        test_duration = assessment_generation_class_data.test_duration
        number_of_total_attempts = assessment_generation_class_data.number_of_attempts
        category = kwargs.get("category")
        current_attempt_count = AssessmentAttemptRepository.number_of_attempts_expired(
            assessment_generation_config_id=assessment_generation_id, user_id=user.id
        )
        
        if assessment_generation_class_data.start_date is not None and assessment_generation_class_data.end_date is not None:
            is_locked = not (assessment_generation_class_data.start_date <= timezone.now() <= assessment_generation_class_data.end_date)
        else:
            is_locked=False
        
        if is_locked:
            raise ValueError("Assessment is locked")

        if current_attempt_count >= number_of_total_attempts:
            raise ValueError("Maximum number of attempts reached")

        module_name = "evaluation.assessment.assessment_classes"
        module = importlib.import_module(module_name)
        assessment_class = getattr(module, class_name)

        if (
            class_name == "MockInterviewBasedRandomAssessment"
            and assessment_generation_details is not None
        ):
            assessment_creation_instance = assessment_class(
                assessment_generation_id, assessment_generation_details
            )
        elif (
            class_name == "MockInterviewBasedRandomAssessment"
            and assessment_generation_details is None
        ):
            raise ValueError(
                "Assessment generation details required in body for mock interview based assessment generation"
            )
        else:
            assessment_creation_instance = assessment_class(assessment_generation_id)

        generated_assessment_data = (
            assessment_creation_instance.generate_assessment_attempt(user)
        )

        if generated_assessment_data.get("assessment_url"):
            start_time = timezone.now()
            assessment_id = (
                AssessmentAttemptRepository.add_or_update_assessment_attempt(
                    start_time=start_time,
                    user=user,
                    test_duration=test_duration,
                    assessment_generation_id=assessment_generation_class_data,
                    assessment_url=generated_assessment_data.get("assessment_url"),
                    report_id=generated_assessment_data.get("report_id"),
                    status=AssessmentAttempt.Status.IN_PROGRESS,
                    type=category,
                )
            )
        else:
            assessment_id = (
                AssessmentAttemptRepository.add_or_update_assessment_attempt(
                    test_duration=test_duration,
                    assessment_generation_id=assessment_generation_class_data,
                    type=generated_assessment_data["category"],
                    status=AssessmentAttempt.Status.IN_PROGRESS,
                    question_list=generated_assessment_data["questions"],
                    user=user,
                )
            )

        generated_assessment_data["assessment_id"] = assessment_id

        buffer_duration_minutes = int(settings.BUFFER_DURATION_MINUTES)
        buffer_duration = timedelta(minutes=buffer_duration_minutes)
        total_delay = test_duration + buffer_duration * 2
        total_delay_seconds = total_delay.total_seconds()
        mark_test_abandoned.apply_async(
            (assessment_id, user.id), countdown=total_delay_seconds
        )
        return generated_assessment_data

    def fetch_assessment_scorecard_by_id(assessment_id):
        assessment = AssessmentAttemptRepository.fetch_assessment_attempt(assessment_id)
        scorecard = AssessmentUseCase.fetch_assessment_scorecard(assessment)
        return scorecard

    def fetch_assessment_scorecard(assessment: AssessmentAttempt):
        type = assessment.type
        heading = ""
        for choice in AssessmentAttempt.Type.choices:
            if int(choice[0]) == int(type):
                heading = choice[1]
                break
        evaluation_data = assessment.eval_data
        resp_data = {
            "heading": heading,
            "last_attempt": assessment.start_time,
            "type": type,
            "status": assessment.status,
        }
        if assessment.eval_data.get("percentage"):
            resp_data["percentage"] = assessment.eval_data.get("percentage")

        resp_data.update(evaluation_data)

        return resp_data

    def fetch_scorecard(user_id):
        assessment = AssessmentAttemptRepository.fetch_all_assessment_attempts(user_id)

        final_resp = []
        for item in assessment:
            resp_data = AssessmentUseCase.fetch_assessment_scorecard(item)
            final_resp.append(resp_data)

        return final_resp

    def exit_assessment(assessment):
        AssessmentAttemptRepository.add_or_update_assessment_attempt(
            assessment_attempt=assessment,
            closed=True,
            status=AssessmentAttempt.Status.ABANDONED,
        )
        return

    def fetch_history_data(user_id):
        available_assessments = AssessmentAttemptRepository.fetch_assessment_configs()

        # Initialize response containers
        filter_options = []
        resp_data = []

        # Build filter options in one pass
        for assessment in available_assessments:
            if (assessment.assessment_generation_id == int(AssessmentAttempt.Type.CODING) + 1 
                and str(user_id) not in settings.USER_IDS_CODING_TEST_ENABLED):
                continue
                
            filter_options.append({
                "name": assessment.assessment_display_name,
                "type": assessment.kwargs.get("category"), 
                "shortForm": "".join(word[0].upper() for word in assessment.assessment_display_name.split())
            })

        # Fetch history with all needed fields in one query
        history = AssessmentAttemptRepository.fetch_user_assessment_history(user_id)

        # Process history items efficiently
        for item in history:
            eval_data = item.get("eval_data", {})
            additional_data = eval_data.get("additional_data", {})

            # Get counts with defaults
            total_correct = additional_data.get("correct", 0)
            total_incorrect = additional_data.get("incorrect", 0) 
            total_not_attempted = additional_data.get("not_attempted", 0)

            # Calculate totals
            total = total_correct + total_incorrect + total_not_attempted
            total_marks_obtained = total_correct * 3
            total_marks_lost = total_incorrect * 1
            total_obtained = total_marks_obtained - total_marks_lost
            grand_total = total * 3

            # Get module info efficiently with select_related
            module_name = None
            course_code = None
            assessment_config_id = item.get("assessment_generation_config_id")
            
            from course.models import Module
            module_info = Module.objects.filter(
                assignment_configs__assessment_generation_id=assessment_config_id
            ).select_related('course').only('title', 'course__code').first()

            if module_info:
                module_name = module_info.title
                course_code = module_info.course.code

            # Build response object
            resp_data.append({
                "last_attempted": item.get("start_time"),
                "assessment_id": item.get("assessment_id"),
                "type": item.get("type"),
                "status": item.get("status"),
                "percentage": eval_data.get("percentage"),
                "short_description": eval_data.get("short_description"),
                "total_correct": total_correct,
                "total_marks_obtained": total_marks_obtained,
                "total_marks_lost": total_marks_lost,
                "total_obtained": total_obtained,
                "grand_total": grand_total,
                "total_incorrect": total_incorrect,
                "total_not_attempted": total_not_attempted,
                "total": total,
                "assessment_name": item.get("assessment_generation_config_id__assessment_display_name"),
                "module_name": module_name,
                "course_code": course_code,
                "assessment_config_id": item.get("assessment_generation_config_id")
            })

        return {
            "filter_options": filter_options,
            "attempted_list": resp_data
        }


class EvaluationUseCase:

    def update_activity_data(user_id: str):
        today = timezone.now().date()
        user_profile = UserProfileRepository.get(user_id=user_id)

        last_task_date = user_profile.last_task_date

        if today != last_task_date:
            # if last_task_date is not Today, then we have to update streak data
            yesterday = today - timedelta(days=1)
            if last_task_date and last_task_date == yesterday:
                # if last task task date was Yesterday, then continue the steak
                user_profile.daily_streak += 1
            else:
                # else, start from 1
                user_profile.daily_streak = 1

            if user_profile.daily_streak > user_profile.longest_streak:
                user_profile.longest_streak = user_profile.daily_streak

            user_profile.last_task_date = today
            user_profile.activity_dates.append(today.isoformat())

            user_profile.save()

    def save_audio_url_speaking(user, question_id, assessment):
        question = QuestionRepository.fetch_question(question_id)

        if question.answer_type == int(Question.AnswerType.VOICE.value):
            user_question_attempt = (
                UserEvalQuestionAttemptRepository.fetch_user_question_attempt(
                    user, question_id, assessment
                )
            )

            if user_question_attempt and user_question_attempt.answer_audio_url:
                return user_question_attempt.answer_audio_url

            user_question_attempt = (
                UserEvalQuestionAttemptRepository.create_user_question_attempt(
                    user, question_id, assessment
                )
            )
            az_storage_service = AzureStorageService()
            audio_path = user_question_attempt.audio_path
            container_name = AudioURLProvider.get_storage_container_name()
            answer_audio_url = az_storage_service.generate_blob_access_url(
                container_name=container_name,
                blob_name=audio_path,
                expiry_time=datetime.now() + timedelta(days=1),
                allow_read=True,
                allow_write=True,
            )
            UserEvalQuestionAttemptRepository.save_user_question_attempt(
                user_question_attempt, answer_audio_url=answer_audio_url
            )

            return answer_audio_url

    def save_question_attempt(
        assessment_id, user, question_id, section, answer_type=None, answer=None
    ):

        assessment_attempt = (
            AssessmentUseCase.fetch_assessment_data_and_assert_validity(
                assessment_id, user.id
            )
        )
        user_attempt = UserEvalQuestionAttemptRepository.fetch_user_question_attempt(
            user, question_id, assessment_attempt
        )
        if not user_attempt:
            user_attempt = (
                UserEvalQuestionAttemptRepository.create_user_question_attempt(
                    user, question_id, assessment_attempt
                )
            )

        kwargs = {}
        if answer_type is not None and answer is not None:
            kwargs[answer_type] = answer
        UserEvalQuestionAttemptRepository.save_user_question_attempt(
            user_attempt, status=UserEvalQuestionAttempt.Status.ATTEMPTED, **kwargs
        )

        if section is not None:
            UserEvalQuestionAttemptRepository.save_user_question_attempt(
                user_attempt, section=section
            )
            AssessmentAttemptRepository.add_or_update_assessment_attempt(
                assessment_attempt, last_saved_section=section
            )

        if user_attempt.id not in assessment_attempt.attempted_list:
            AssessmentAttemptRepository.add_or_update_assessment_attempt(
                assessment_attempt,
                last_saved=question_id,
                add_to_attempted_list=user_attempt.id,
            )

        return

    def evaluate_all_questions(assessment):
        AssessmentAttemptRepository.add_or_update_assessment_attempt(
            assessment, closed=True, status=AssessmentAttempt.Status.EVALUATION_PENDING
        )
        if assessment:
            attempted_questions_list = (
                UserEvalQuestionAttemptRepository.fetch_attempted_questions(assessment)
            )
            for user_attempt in attempted_questions_list:
                answer_type = None
                if user_attempt.mcq_answer is not None:
                    answer_type = "mcq_answer"
                elif user_attempt.multiple_mcq_answer is not None:
                    answer_type = "multiple_mcq_answer"
                elif user_attempt.answer_text is not None:
                    answer_type = "answer_text"
                elif user_attempt.answer_audio_url is not None:
                    answer_type = "voice"
                elif user_attempt.code_stubs is not None:
                    answer_type = "code"
                    test_cases_data = user_attempt.eval_data.get("test_cases", [])
                    num_test_cases_passed = sum(
                        1
                        for test_case in test_cases_data
                        if test_case.get("passed", False)
                    )
                    total_test_cases = len(test_cases_data)
                    score = (num_test_cases_passed / total_test_cases) * 50
                    test_cases_eval_data = {
                        "code_correctness_score": {
                            "code_correctness_score": int(score),
                            "total_test_cases": int(total_test_cases),
                            "num_test_cases_passed": int(num_test_cases_passed),
                        }
                    }
                    AssessmentAttemptRepository.add_or_update_assessment_attempt(
                        assessment, eval_data=test_cases_eval_data
                    )
                evaluator_class_name = evaluator_mapping.get(answer_type)
                if evaluator_class_name:
                    evaluator_module = importlib.import_module(
                        f"evaluation.evaluators.{evaluator_class_name}"
                    )
                    evaluator = getattr(evaluator_module, evaluator_class_name)
                    evaluation_instance = evaluator(question_attempt=user_attempt)
                    evaluation_instance.evaluate()

            assessment_evaluator: AssessmentEvaluator = None
            if assessment.type == int(AssessmentAttempt.Type.LANGUAGE):
                assessment_evaluator = LanguageAssessmentEvaluator(assessment)
            elif assessment.type == int(AssessmentAttempt.Type.LOGIC):
                assessment_evaluator = LogicalAssessmentEvaluator(assessment)
            elif assessment.type == int(AssessmentAttempt.Type.PERSONALITY):
                assessment_evaluator = PersonalityAssessmentEvaluator(assessment)
            elif assessment.type == int(AssessmentAttempt.Type.DSA_PRACTICE):
                assessment_evaluator = DSAAssessmentEvaluator(assessment)
            elif assessment.type == int(AssessmentAttempt.Type.MOCK_BEHAVIOURAL):
                assessment_evaluator = MockInterviewBehaviouralEvaluator(assessment)
            elif assessment.type == int(AssessmentAttempt.Type.LSRW):
                assessment_evaluator = LSRWAssessmentEvaluator(assessment)

            assessment_evaluator.evaluate()


class XobinUseCase:

    def generate_xobin_assessment_url(user, assessment_id):

        user_details = (
            UserProfileRepository.fetch_user_data(user.id).get("entire_data").first()
        )
        name = user_details.get("name")
        email = user_details.get("email")
        if email is None:
            email = user.email
        if name is None:
            name = user.username

        expiry_time = datetime.now() + timedelta(weeks=10)
        expiry_time_formatted = expiry_time.strftime("%Y-%m-%d %H:%M:%S")

        xobin_service = XobinAssessmentService()
        sample_response = {
            "report_id": 1892377,
            "assessment_url": "https://aspireworks.xobin.com/wc/assessment/1OA4TQ20MURQ?inviteToken=FDF893FEB2A4B4802MBE79IA357520B55EA599DFA00EBC7129A6CBB754F66E2783FBCE6F28",
        }
        return sample_response
        # return xobin_service.invite_candidate(name, email, assessment_id, expiry_time_formatted)

    def save_xobin_result(data):
        report_id = data.get("id")

        assessment = AssessmentAttemptRepository.fetch_assessment_from_report_id(
            report_id
        )

        percentage = data.get("overall_percentage")
        additional_data = {
            "sections": data.get("sections"),
        }
        eval_data = {"percentage": percentage, "additional_data": additional_data}
        logger.info(
            f"Saving Xobin result for assessment {assessment.assessment_id} - {eval_data}"
        )
        AssessmentAttemptRepository.add_or_update_assessment_attempt(
            assessment,
            closed=True,
            status=AssessmentAttempt.Status.COMPLETED,
            eval_data=eval_data,
            evaluation_triggered=True,
        )

    def verify_webhook(data, hmac_header):
        apikey = settings.XOBIN_API_KEY

        if isinstance(data, dict):
            logger.info("converting dict to str for encoding")
            data = json.dumps(data)
        digest = hmac.new(
            apikey.encode("utf-8"), data.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()

        computed_hmac = base64.urlsafe_b64encode(digest).rstrip(b"=")

        return hmac.compare_digest(computed_hmac, hmac_header.encode("utf-8"))


class XobinAssessmentService(BaseRestService):
    TIMEOUT = 100
    CONNECTION_TIMEOUT = 100

    def __init__(self, **kwargs):
        self.secret_token = settings.XOBIN_API_KEY
        super().__init__(**kwargs)

    def get_base_headers(self):
        return {"apiKey": self.secret_token, "Content-Type": "application/json"}

    def get_base_url(self) -> str:
        return settings.XOBIN_ENDPOINT

    def invite_candidate(
        self, name: str, email: str, assessment_id: str, expiry_time: str
    ):
        api_url = f"{self.get_base_url()}assessments/invite"
        request_body = {
            "candidate_name": name,
            "candidate_email": email,
            "assessment_id": assessment_id,
            "invite_format": "getlink",
            "expiry_date": expiry_time,
        }
        response = self._post_request(
            url=api_url, data=request_body, custom_headers=self.get_base_headers()
        )

        if response.status_code == 200:
            response_data = response.json()
            return {
                "report_id": response_data.get("report_id"),
                "assessment_url": response_data.get("invite_link"),
            }
        else:
            logger.error(f"Error in generating Xobin assessment URL: {response.text}")
            raise ValueError("Error in generating Xobin assessment URL")


class DSAPracticeUsecase:

    @staticmethod
    def save_run_execution_log(
        *,
        user_id: int,
        question_id: int,
        assessment_id: int,
        duration: float,
        submit=False,
    ):
        c_log = CompileDurationLog(
            timestamp=int(datetime.now().timestamp()), duration=duration
        )
        DSAPracticeChatDataRepository.save_run_log(
            compile_duration_log=c_log,
            user_id=user_id,
            question_id=question_id,
            assessment_attempt_id=assessment_id,
            submit=submit,
        )

    @staticmethod
    def call_executor(
        user,
        question_id,
        assessment_id,
        type_of_evaluation,
        language,
        code,
        custom_testcases,
    ):
        assessment_attempt_id = (
            AssessmentUseCase.fetch_assessment_data_and_assert_validity(
                assessment_id, user.id
            )
        )
        user_attempt = UserEvalQuestionAttemptRepository.fetch_user_question_attempt(
            user, question_id, assessment_attempt=assessment_attempt_id
        )
        code_stubs = user_attempt.code_stubs
        code_stubs[language] = code
        UserEvalQuestionAttemptRepository.save_user_question_attempt(
            user_attempt, code=code, code_stubs=code_stubs
        )
        # todo we hae to keep only the code of language for which user submits code not for all
        if user_attempt.id not in assessment_attempt_id.attempted_list:
            AssessmentAttemptRepository.add_or_update_assessment_attempt(
                assessment_attempt=assessment_attempt_id,
                last_saved=question_id,
                add_to_attempted_list=user_attempt.id,
            )
        question_data = AssessmentUseCase.fetch_question_data(
            question_id, assessment_attempt_id, user, for_exeution=True
        )
        if type_of_evaluation == "run":
            test_cases = question_data["exampleTestcases"]
            test_cases.extend(custom_testcases)
            main_code = None
            if language == "cpp":
                main_code = question_data["driver_codes"]["cpp"]["main_code"]
            elif language == "java":
                main_code = question_data["driver_codes"]["java"]["main_code"]
            elif language == "python":
                main_code = question_data["driver_codes"]["python"]["main_code"]
            elif language == "javascript":
                main_code = question_data["driver_codes"]["javascript"]["main_code"]
            a = datetime.now()
            DSAPracticeExecutor(
                user_attempt, test_cases, language, code, main_code
            ).evaluate()
            DSAPracticeUsecase.save_run_execution_log(
                user_id=user.id,
                question_id=question_id,
                assessment_id=assessment_id,
                duration=(datetime.now() - a).total_seconds(),
            )
        elif type_of_evaluation == "submit":
            test_cases = question_data["exampleTestcases"]
            additional_test_cases = question_data.get("additionalTestcases", [])
            test_cases.extend(additional_test_cases)
            main_code = None
            if language == "cpp":
                main_code = question_data["driver_codes"]["cpp"]["main_code"]
            elif language == "java":
                main_code = question_data["driver_codes"]["java"]["main_code"]
            elif language == "python":
                main_code = question_data["driver_codes"]["python"]["main_code"]
            elif language == "javascript":
                main_code = question_data["driver_codes"]["javascript"]["main_code"]
            a = datetime.now()
            DSAPracticeExecutor(
                user_attempt, test_cases, language, code, main_code
            ).evaluate()
            DSAPracticeUsecase.save_run_execution_log(
                user_id=user.id,
                question_id=question_id,
                assessment_id=assessment_id,
                duration=(datetime.now() - a).total_seconds(),
                submit=True,
            )

    @staticmethod
    def get_execution_status(user, assessment_id, question_id):
        assessment = AssessmentUseCase.fetch_assessment_data_and_assert_validity(
            assessment_id, user.id
        )
        user_question_attempt = (
            UserEvalQuestionAttemptRepository.fetch_user_question_attempt(
                user, question_id, assessment
            )
        )
        return user_question_attempt.eval_data


class DSAChatHistoryUseCase:

    @classmethod
    def get_proactive_msg(cls, *, message_text: str, old_format=False) -> dict:
        if old_format:
            return {
                "message": message_text,
                "type": "bot",
                "system_generated": True,
            }
        return {
            "content": message_text,
            "role": "assistant",
            "system_generated": True,
        }

    @classmethod
    def get_msg_text_and_delay_for_proactive_msg(
        cls, user_id: int
    ) -> typing.Tuple[str, int]:
        has_previously_completed_assessments = (
            AssessmentAttemptRepository.fetch_all_assessments_completed(
                user_id=user_id
            ).exists()
        )
        config = ConfigMapRepository.get_config_by_tag(
            tag=ConfigMapRepository.PROACTIVE_BOT_MESSAGES
        )
        message_text = config[
            "repeat" if has_previously_completed_assessments else "first"
        ]
        delay = config["delay"]
        return message_text, 2

    @classmethod
    def get_chat_history(
        cls, is_superuser, user_id, question_id, assessment_attempt_id
    ):
        user_data, created = DSAPracticeChatDataRepository.get_or_create(
            user_id=user_id,
            question_id=question_id,
            assessment_attempt_id=assessment_attempt_id,
        )
        if user_data.chat_history_obj is None:
            message_text, delay = cls.get_msg_text_and_delay_for_proactive_msg(
                user_id=user_id
            )

            # Not adding to chat history here since we don't have context vars,
            # this msg will only be added chat history when chat is initiated from user.
            message = cls.get_proactive_msg(message_text=message_text, old_format=True)

            message.update(
                {"open_chat_window": True, "is_proactive_message": True, "delay": delay}
            )
            return [message]
        else:
            lis = []
            ChatHistoryRepository(user_data.chat_history_obj.id).get_msg_list_for_llm()
            lis = LLMCommunicationWrapper.get_processed_chat_messages(
                chat_history=user_data.chat_history_obj.chat_history,
                is_superuser=is_superuser,
            )
            return lis

    @staticmethod
    def get_full_chat_history(user_id, question_id, assessment_attempt_id):
        user_data, created = DSAPracticeChatDataRepository.get_or_create(
            user_id=user_id,
            question_id=question_id,
            assessment_attempt_id=assessment_attempt_id,
        )
        if created:
            return []

        # Return the entire chat history in its original form
        return user_data.chat_history_obj.chat_history


class DSAReportUsecase:
    def get_total_score(eval_data):
        total_score = (
            eval_data.get("code_quality_score", {}).get("Score", 0)
            + eval_data.get("code_efficiency_score", {}).get("Score", 0)
            + eval_data.get("code_correctness_score", {}).get(
                "code_correctness_score", 0
            )
        )
        return total_score

    def generate_report(user, attempt, question):
        full_name = UserProfileRepository.get_user_fullname(user.id)
        eval_data = attempt.eval_data
        status = attempt.status
        total_test_cases = eval_data.get("code_correctness_score", {}).get(
            "total_test_cases", 0
        )
        test_cases_passed = eval_data.get("code_correctness_score", {}).get(
            "num_test_cases_passed", 0
        )
        test_cases_data = UserEvalQuestionAttemptRepository.fetch_user_question_attempt(
            user, question.id, attempt
        ).eval_data.get("test_cases", [])
        failed_test_cases = [
            test_case
            for test_case in test_cases_data
            if test_case.get("passed") is False
            or test_case.get("error_type") is not None
        ]
        failed_test_cases = (
            failed_test_cases[:10] if len(failed_test_cases) > 10 else failed_test_cases
        )
        submitted_code = UserEvalQuestionAttemptRepository.fetch_user_question_attempt(
            user, question.id, attempt
        ).code
        # Check if all required scores are present
        scores_available = (
            eval_data.get("code_correctness_score", {}).get("code_correctness_score")
            is not None
            and eval_data.get("code_efficiency_score", {}).get("Score") is not None
            and eval_data.get("code_quality_score", {}).get("Score") is not None
        )

        detailed_report = (
            True
            if total_test_cases != 0
            and eval_data.get("code_correctness_score", {}).get(
                "code_correctness_score", 0
            )
            > 10
            else False
        )

        report = {
            "top": {
                "student_name": full_name,
                "date_of_session": str(attempt.updated_at.date()),
                "title_of_the_dsa_problem": question.question_data.get(
                    "questionTitle", ""
                ),
                "difficulty_level_and_tags": question.question_data.get(
                    "difficulty", ""
                ),
            },
            "total_score": {
                "score": (
                    DSAReportUsecase.get_total_score(eval_data)
                    if scores_available
                    else None
                ),
                "overall_feedback": eval_data.get("code_summary", {}).get(
                    "OverallSummary", None
                ),
            },
            "detailed_performance_analysis": {
                "correctness": {
                    "score": (
                        eval_data.get("code_correctness_score", {}).get(
                            "code_correctness_score", 0
                        )
                        if total_test_cases > 0
                        else None
                    ),
                    "feedback": (
                        f"Test cases passed: {test_cases_passed}/{total_test_cases}"
                        if total_test_cases > 0
                        else None
                    ),
                    "failed_tests": (
                        failed_test_cases if len(failed_test_cases) > 0 else None
                    ),
                },
                "report_not_generated_reasoning": (
                    "Not enough test cases passed to generate detailed feedback. Please review solution and re-attempt the question"
                    if not detailed_report
                    else None
                ),
                "efficiency": {
                    "score": eval_data.get("code_efficiency_score", {}).get(
                        "Score", None
                    ),
                    "time_complexity": eval_data.get("code_efficiency_score", {}).get(
                        "timecomplexity", None
                    ),
                    "space_complexity": eval_data.get("code_efficiency_score", {}).get(
                        "spacecomplexity", None
                    ),
                    "optimum_time_complexity": eval_data.get(
                        "code_efficiency_score", {}
                    ).get("optimumtimecomplexity", None),
                },
                "code_quality": {
                    "score": eval_data.get("code_quality_score", {}).get("Score", 0),
                    "code_readability": eval_data.get("code_quality_score", {})
                    .get("Feedback", {})
                    .get("CodeReadabilityBestPractices", None),
                    "variable_naming": eval_data.get("code_quality_score", {})
                    .get("Feedback", {})
                    .get("VariableNaming", None),
                    "code_structure": eval_data.get("code_quality_score", {})
                    .get("Feedback", {})
                    .get("CodeStructure", None),
                    "usage_of_comments": eval_data.get("code_quality_score", {})
                    .get("Feedback", {})
                    .get("UsageOfComments", None),
                },
                "improvement_and_learning": {
                    "score": 0,
                    "feedback": eval_data.get("code_improvement_score", {}).get(
                        "Feedback", None
                    ),
                },
            },
            "session_insights": {
                "key_strengths": eval_data.get("code_summary", {}).get(
                    "StrongPoints", None
                ),
                "areas_for_improvement": eval_data.get("code_summary", {}).get(
                    "AreaOfImprovements", None
                ),
            },
            "revision_topics": eval_data.get("code_revision_topics", None),
            "resources": {
                "article_link": question.question_data.get("resources", {}).get(
                    "article_link", ""
                ),
                "video_link": question.question_data.get("resources", {}).get(
                    "video_link", ""
                ),
            },
            "submitted_code": submitted_code,
            "footer": {
                "encouraging_note": "Keep practicing and utilizing the platform resources to improve your coding skills!"
            },
            "status": status,
            "detailed_report": detailed_report,
        }

        return report


class DSABotWebsocketConsumerUseCase:
    @staticmethod
    def _substitue_in_prompt(code, question, language, run_result, name):
        prompt_template = PromptTemplateRepository.get_prompt_object(
            PromptTemplateRepository.PromptName.DSA_PRACTICE.value
        )
        src = Template(prompt_template.prompt)
        result = src.substitute(
            run_result=run_result,
            code=code,
            question=question,
            language=language,
            name=name,
        )
        return result

    @staticmethod
    def _call_gpt(
        user_input, conversational_history, code, question, language, run_result, name
    ):
        llm = OpenAIService()

        prompt = DSABotWebsocketConsumerUseCase._substitue_in_prompt(
            code, question, language, run_result, name
        )
        sanitized_prompt = PromptTemplateRepository.sanitize_prompt(prompt)

        logger.info(f"Giving prompt to GPT: {sanitized_prompt}")

        messages = [
            {
                "role": "system",
                "content": sanitized_prompt,
            }
        ]
        prompt_template = PromptTemplateRepository.get_prompt_object(
            PromptTemplateRepository.PromptName.DSA_PRACTICE.value
        )

        # Create a copy of conversational history without code for OpenAI call
        conversational_history_for_gpt = (
            DSABotWebsocketConsumerUseCase.convert_chat_history_to_openai_spec(
                conversational_history, remove_code=True
            )
        )

        messages.extend(conversational_history_for_gpt)
        messages.append(
            {
                "role": "user",
                "content": user_input + prompt_template.additional_guardrail_prompt,
            }
        )

        logger.info(f"Sending final msgs: {messages}")
        completion = llm.get_completion_from_messages(
            messages, llm_config_name_options=["dsa_chat_gpt_1", "dsa_chat_gpt_2"]
        )

        return completion

    @staticmethod
    def convert_chat_history_to_openai_spec(
        conversational_history: List, remove_code=False
    ) -> typing.List[typing.Dict]:
        to_return = []
        for msg_dict in conversational_history:
            new_msg = {}
            if msg_dict["type"] == "bot":
                new_msg["role"] = "assistant"
                if remove_code and "code" in msg_dict:
                    msg_dict = msg_dict.copy()
                    msg_dict.pop("code")
            else:
                new_msg["role"] = "user"
            new_msg["content"] = msg_dict["message"]
            to_return.append(new_msg)
        return to_return

    @staticmethod
    def handle_request_2(
        user_input,
        user_id,
        question_id,
        assessment_attempt_id,
        code,
        language,
        run_result,
    ):
        dsa_practice_data, _ = DSAPracticeChatDataRepository.get_or_create(
            user_id=user_id,
            question_id=question_id,
            assessment_attempt_id=assessment_attempt_id,
        )
        question_text = QuestionRepository.fetch_question(
            question_id=question_id
        ).question_data["question"]
        name = UserProfileRepository.get_user_fullname(user_id=user_id)
        context = {
            "code": code,
            "question": question_text,
            "language": language,
            "run_result": run_result,
            "name": name,
        }
        if dsa_practice_data.chat_history_obj is None:
            llm_wrapper = LLMCommunicationWrapper(
                prompt_name=ValidPromptTemplates.DSA_PRACTICE,
                chat_history_id=None,
                initialize=True,
                initializing_context_vars=context,
            )
            message_text, _ = (
                DSAChatHistoryUseCase.get_msg_text_and_delay_for_proactive_msg(
                    user_id=user_id
                )
            )
            # Adding this proactive msg here since we have context vars here, it might have been already been
            # displayed to user thought the chat history view.
            message = DSAChatHistoryUseCase.get_proactive_msg(message_text=message_text)
            llm_wrapper.chat_history_repository.add_msgs_to_chat_history(
                [message], commit_to_db=True
            )
            DSAPracticeChatDataRepository.add_chat_history_id(
                dsa_practice_data=dsa_practice_data,
                chat_history_id=llm_wrapper.get_chat_history_object().id,
            )
        else:
            llm_wrapper = LLMCommunicationWrapper(
                prompt_name=ValidPromptTemplates.DSA_PRACTICE,
                chat_history_id=dsa_practice_data.chat_history_obj.id,
            )

        response_text = llm_wrapper.send_user_message_and_get_response(
            user_input, context
        )
        return response_text

    @staticmethod
    def handle_request(
        user_input,
        user_id,
        question_id,
        assessment_attempt_id,
        code,
        language,
        run_result,
    ):
        user_msg_timestamp = int(datetime.now().timestamp())
        user_data, _ = DSAPracticeChatDataRepository.get_or_create(
            user_id=user_id,
            question_id=question_id,
            assessment_attempt_id=assessment_attempt_id,
        )
        conversational_history = user_data.chat_history
        question_text = QuestionRepository.fetch_question(
            question_id=question_id
        ).question_data["question_without_html"]
        response = None

        try:
            name = UserProfileRepository.get_user_fullname(user_id=user_id)
            name = name if name != "" else "User"
            response = DSABotWebsocketConsumerUseCase._call_gpt(
                user_input,
                conversational_history,
                code,
                question_text,
                language,
                run_result,
                name,
            )

            bot_msg_timestamp = int(datetime.now().timestamp())

            if user_msg_timestamp is not None and bot_msg_timestamp is not None:
                message_generation_time = bot_msg_timestamp - user_msg_timestamp
            else:
                message_generation_time = None

            DSAPracticeChatDataRepository.update_chat_history(
                user_data=user_data,
                user_msg=user_input,
                bot_msg=response,
                user_msg_timestamp=user_msg_timestamp,
                bot_msg_timestamp=bot_msg_timestamp,
                message_generation_time=message_generation_time,
                code=code,
            )
        except openai._exceptions.RateLimitError as e:
            response = "Could not process the input at the moment. Please try again."

        return response


class DSAQuestionsUsecase:
    @staticmethod
    def _get_lab_question_list(user, solved_question_ids):
        # today_date = date.today()
        # institute_id = UserProfileRepository.get(user_id=user.id).institute_id
        # question_list = QuestionListRepository.get_question_list_by_institute_id(institute_id)

        # if institute_id and question_list:
        #     # Check if a session is already created for the day
        #     dsa_session = DSASessionRepository.get_dsa_session(user=user, date=today_date)
        #     if dsa_session:
        #         # If a session exists, fetch those questions
        #         question_ids = dsa_session.question_ids
        #         questions = QuestionRepository.fetch_questions_by_ids(question_ids)
        #     else:
        #         # If no session exists, fetch questions for the institute
        #         question_ids = question_list['question_ids']
        #         questions = QuestionRepository.fetch_questions_by_ids(question_ids)

        #         # Filter out solved questions
        #         unsolved_questions = [question for question in questions if question.id not in solved_question_ids]

        #         # Select 2 random unsolved questions
        #         random_questions = sample(unsolved_questions, min(2, len(unsolved_questions)))
        #         questions = random_questions
        #         question_ids = [question.id for question in questions]
        #         DSASessionRepository.create_dsa_session(user=user, date=today_date, question_ids=question_ids)
        # else:
        # If no institute is associated with the user, fetch DSA practice questions
        questions = QuestionRepository.return_questions_by_category(
            int(Question.Category.DSA_PRACTICE), None, []
        )
        return questions

    @staticmethod
    def get_question_list(user, lab=False):
        successful_assessment_attempts = (
            AssessmentAttemptRepository.fetch_all_assessments_completed(user.id)
        )
        solved_question_ids = {
            attempt.question_list[0]["questions"][0]
            for attempt in successful_assessment_attempts
        }

        if lab:
            questions = DSAQuestionsUsecase._get_lab_question_list(
                user, solved_question_ids
            )
        else:
            questions = QuestionRepository.return_questions_by_category(
                int(Question.Category.DSA_PRACTICE), None, []
            )

        questions_list = []
        topics_set = set()
        companies_set = set()

        dsa_sheet_names = DSASheetConfigRepository.get_all_configs()

        for question in questions:
            locked = False
            if question.source is not None:
                locked = False
            question_data = {
                "id": question.id,
                "title": question.question_data["questionTitle"],
                "difficulty": question.question_data["difficulty"],
                "topics": question.tags,
                "companies": question.question_data["companies"],
                "locked": locked,
                "score": None,
            }

            for attempt in successful_assessment_attempts:
                if question.id in attempt.question_list[0]["questions"]:
                    if question.id in solved_question_ids:
                        question_data["score"] = DSAReportUsecase.get_total_score(
                            attempt.eval_data
                        )
                    else:
                        question_data["score"] = None
                    break

            questions_list.append(question_data)
            for topic in question.tags:
                topics_set.add(topic)
            for company in question.question_data["companies"]:
                companies_set.add(company)

        # Define a difficulty order
        difficulty_order = {"basic": 0, "easy": 1, "medium": 2, "hard": 3}

        # Sort questions by difficulty and locked status
        questions_list = sorted(
            questions_list,
            key=lambda x: (
                x["locked"],
                difficulty_order[x["difficulty"].lower()],
                x["id"],
            ),
        )
        topics_list = sorted(list(topics_set))
        return DSAQuestionsResponse(
            dsa_sheet_names, questions_list, topics_list, companies_set
        )

    @staticmethod
    def get_code_stubs(question_id, assessment_id, user):
        assessment_attempt = AssessmentAttemptRepository.get_assessment_data(
            assessment_id, user.id
        )
        question_data = AssessmentUseCase.fetch_question_data(
            question_id, assessment_attempt, user, for_exeution=True
        )
        driver_codes = question_data["driver_codes"]
        user_codes = {lang: code["user_code"] for lang, code in driver_codes.items()}
        for lang, code in user_codes.items():
            user_codes[lang] = code.lstrip("\r\n")
        return user_codes

    @staticmethod
    def generate_attempt_by_question_id(user, question_id, mode):
        question = QuestionRepository.fetch_question(question_id)
        institute_id = UserProfileRepository.get(user_id=user.id).institute_id
        difficulty = question.question_data.get("difficulty")

        # if mode is eval and the user is assigned to an institute which has lab questions, then evaluation else practice
        # if mode == AssessmentAttempt.Mode.EVALUATION and institute_id and QuestionListRepository.exists(institute_id):
        #     assessment_mode = AssessmentAttempt.Mode.EVALUATION
        # else:
        assessment_mode = AssessmentAttempt.Mode.PRACTICE

        if assessment_mode is AssessmentAttempt.Mode.EVALUATION:
            if difficulty == "basic":
                required_time = "00:30:00"
            elif difficulty == "easy":
                required_time = "00:30:00"
            elif difficulty == "medium":
                required_time = "00:45:00"
            elif difficulty == "hard":
                required_time = "01:00:00"
        else:
            required_time = "23:59:59"

        assessment_generation_class_data = AssessmentGenerationConfigRepository.return_assessment_generation_class_data(
            5
        )
        generated_assessment_data = {
            "total_number": 1,
            "category": int(Question.Category.DSA_PRACTICE),
            "questions": [
                {
                    "section": question.question_data["difficulty"],
                    "questions": [question.id],
                    "skippable": False,
                }
            ],
        }

        assessment_id = AssessmentAttemptRepository.add_or_update_assessment_attempt(
            test_duration=required_time,
            assessment_generation_id=assessment_generation_class_data,
            type=generated_assessment_data["category"],
            status=AssessmentAttempt.Status.IN_PROGRESS,
            question_list=generated_assessment_data["questions"],
            user=user,
            mode=assessment_mode,
        )
        generated_assessment_data["assessment_id"] = assessment_id
        user_codes = DSAQuestionsUsecase.get_code_stubs(
            question_id=question_id, assessment_id=assessment_id, user=user
        )
        current_assessment = AssessmentAttemptRepository.fetch_assessment_attempt(
            assessment_id=assessment_id
        )
        user_attempt = UserEvalQuestionAttemptRepository.create_user_question_attempt(
            user=user, question_id=question_id, assessment_attempt_id=current_assessment
        )
        UserEvalQuestionAttemptRepository.save_user_question_attempt(
            user_attempt,
            status=int(UserEvalQuestionAttempt.Status.ATTEMPTED),
            code_stubs=user_codes,
        )
        return generated_assessment_data


class QuestionIssueUsecase:
    @staticmethod
    def create_issue(
        user, type_of_issue, question_id, assessment_attempt_id, description
    ):
        report_id = QuestionIssuesRepository.save_question_issue(
            user=user,
            type_of_issue=type_of_issue,
            question_id=question_id,
            assessment_attempt_id=assessment_attempt_id,
            description=description,
        )
        return report_id


class DSAPracticeReportHistoryUsecase:
    @staticmethod
    def get_dsa_reports(user_id):
        successful_assessment_attempts = (
            AssessmentAttemptRepository.fetch_all_assessments_completed(user_id)
        )
        all_reports = []
        for attempt in successful_assessment_attempts:
            report_data = {}
            eval_data = attempt.eval_data
            total_score = DSAReportUsecase.get_total_score(eval_data)
            question_id = attempt.question_list[0]["questions"][0]
            question = QuestionRepository.fetch_question(question_id)
            report_data["assessment_id"] = attempt.assessment_id
            report_data["title"] = question.question_data["questionTitle"]
            report_data["date"] = attempt.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            report_data["tags"] = question.tags
            report_data["difficulty"] = question.question_data["difficulty"]
            report_data["score"] = f"{total_score}/100"
            all_reports.append(report_data)

        all_reports.sort(key=lambda x: x["date"], reverse=True)
        return all_reports


class DashBoardDetailsUsecase:
    @staticmethod
    def _calculate_score_sum(attempt, score_type):
        return attempt.eval_data.get(score_type, {}).get("Score", 0)

    @staticmethod
    def _calculate_correctness_score(attempt):
        return attempt.eval_data.get("code_correctness_score", {}).get(
            "code_correctness_score", 0
        )

    @staticmethod
    def _fetch_question_tags(attempt):
        question_id = attempt.question_list[0]["questions"][0]
        question = QuestionRepository.fetch_question(question_id)
        return question.tags

    @staticmethod
    def _calculate_average_score(score_sum, max_score, attempts):
        if len(attempts) > 0:
            return (score_sum * (100 / max_score)) / len(attempts)
        else:
            return 0

    @staticmethod
    def _is_problem_solved(attempt):
        correctness_score = DashBoardDetailsUsecase._calculate_correctness_score(
            attempt
        )
        return correctness_score >= 40

    @staticmethod
    def get_dashboard_details(user_id):
        # Fetch all completed assessment attempts for the user
        assessment_attempts = (
            AssessmentAttemptRepository.fetch_all_assessments_completed(user_id)
        )
        full_name = UserProfileRepository.get_user_fullname(user_id)
        # leaderboard_rank = LeaderboardRepository.get_leaderboard_rank(user_id)
        # Gather all question IDs and attempt IDs
        question_ids = {
            attempt.question_list[0]["questions"][0] for attempt in assessment_attempts
        }
        attempt_ids = {attempt.assessment_id for attempt in assessment_attempts}

        # Pre-fetch all question tags for the relevant question IDs
        questions = QuestionRepository.fetch_questions_by_ids(list(question_ids))
        question_tags_map = {question.id: question.tags for question in questions}

        # Pre-fetch all chat sessions for the relevant attempt IDs and user ID
        chat_sessions = DSAPracticeChatDataRepository.fetch_chat_sessions(
            user_id, list(attempt_ids)
        )
        chat_sessions_map = {
            session.assessment_attempt_id: session.llm_chat_count
            for session in chat_sessions
        }
        successful_assessment_attempts = []
        questions_solved = set()
        total_chat_count = 0
        strengths = set()
        weaknesses = set()
        total_time_spent = 0
        code_quality_sum = 0
        code_efficiency_sum = 0
        code_correctness_sum = 0

        for attempt in assessment_attempts:
            question_id = attempt.question_list[0]["questions"][0]
            questions_solved.add(question_id)
            is_problem_solved = DashBoardDetailsUsecase._is_problem_solved(attempt)
            # Use pre-fetched question tags
            for tag in question_tags_map.get(question_id, []):
                if is_problem_solved:
                    strengths.add(tag)
                elif tag not in strengths:
                    weaknesses.add(tag)

            code_quality_sum += DashBoardDetailsUsecase._calculate_score_sum(
                attempt, "code_quality_score"
            )
            code_efficiency_sum += DashBoardDetailsUsecase._calculate_score_sum(
                attempt, "code_efficiency_score"
            )
            code_correctness_sum += (
                DashBoardDetailsUsecase._calculate_correctness_score(attempt)
            )

            # Use pre-fetched chat sessions
            chat_session_count = chat_sessions_map.get(attempt.assessment_id)
            if chat_session_count:
                total_chat_count += chat_session_count

            # Calculate total time spent
            total_time_spent += (
                (attempt.updated_at - attempt.start_time).total_seconds() / 60
                if isinstance(attempt.updated_at, datetime)
                and isinstance(attempt.start_time, datetime)
                else 0
            )

            if is_problem_solved:
                successful_assessment_attempts.append(attempt)

        # Calculate average scores
        code_quality_avg = DashBoardDetailsUsecase._calculate_average_score(
            code_quality_sum, 20, assessment_attempts
        )
        code_efficiency_avg = DashBoardDetailsUsecase._calculate_average_score(
            code_efficiency_sum, 30, assessment_attempts
        )
        code_correctness_avg = DashBoardDetailsUsecase._calculate_average_score(
            code_correctness_sum, 50, assessment_attempts
        )

        # Prepare the final data dictionary
        # to-do remove total_chat_sessions afterwards
        data = {
            "name": full_name,
            "leaderboard_rank": 0,
            "total_problems_solved": len(questions_solved),
            "total_number_of_attempts": len(assessment_attempts),
            "total_chat_sessions": len(chat_sessions),
            "total_chat_messages": total_chat_count,
            "total_time_spent": total_time_spent,
            "avg_time_per_question": (
                total_time_spent / len(questions_solved) if questions_solved else 0
            ),
            "success_rate": (
                len(successful_assessment_attempts) / len(assessment_attempts) * 100
                if len(assessment_attempts) > 0
                else 0
            ),
            "performance_overview": {
                "code_quality": code_quality_avg,
                "code_efficiency": code_efficiency_avg,
                "code_correctness": code_correctness_avg,
            },
            "strengths": list(strengths),
            "weaknesses": list(weaknesses),
        }
        return data


class DSASheetsConfigUsecase:
    def get_sheet_questions(user, sheet_id):
        dsa_sheet_names = DSASheetConfigRepository.get_all_configs()
        topics_set = set()
        companies_set = set()
        questions_list = []
        question_ids = DSASheetConfigRepository.get_config_questions_list_by_id(
            sheet_id
        )
        if question_ids:
            questions = QuestionRepository.fetch_questions_by_ids(list(question_ids))
        else:
            return DSAQuestionsResponse(
                dsa_sheet_names, questions_list, topics_set, companies_set
            )

        successful_assessment_attempts = (
            AssessmentAttemptRepository.fetch_all_assessments_completed(user.id)
        )
        solved_question_ids = {
            attempt.question_list[0]["questions"][0]
            for attempt in successful_assessment_attempts
        }
        for question in questions:
            locked = True
            if question.source is not None:
                locked = False
            question_data = {
                "id": question.id,
                "title": question.question_data["questionTitle"],
                "difficulty": question.question_data["difficulty"],
                "topics": question.tags,
                "companies": question.question_data["companies"],
                "locked": locked,
                "score": None,
            }

            for attempt in successful_assessment_attempts:
                if question.id in attempt.question_list[0]["questions"]:
                    if question.id in solved_question_ids:
                        question_data["score"] = DSAReportUsecase.get_total_score(
                            attempt.eval_data
                        )
                    else:
                        question_data["score"] = None
                    break

            questions_list.append(question_data)
            for topic in question.tags:
                topics_set.add(topic)
            for company in question.question_data["companies"]:
                companies_set.add(company)

        # Define a difficulty order
        difficulty_order = {"basic": 0, "easy": 1, "medium": 2, "hard": 3}

        # Sort questions by difficulty and locked status
        questions_list = sorted(
            questions_list,
            key=lambda x: (x["locked"], difficulty_order[x["difficulty"].lower()]),
        )
        topics_list = sorted(list(topics_set))
        return DSAQuestionsResponse(
            dsa_sheet_names, questions_list, topics_list, companies_set
        )

    def get_sheet_status(user, sheet_id):
        config_question_ids = DSASheetConfigRepository.get_config_questions_list_by_id(
            sheet_id
        )
        assessment_attempts = (
            AssessmentAttemptRepository.fetch_all_assessments_completed(user_id=user.id)
        )
        solved_question_ids = {
            attempt.question_list[0]["questions"][0] for attempt in assessment_attempts
        }

        solved_config_questions = [
            qid for qid in config_question_ids if qid in solved_question_ids
        ]

        return {
            "solved_count": len(solved_config_questions),
            "total_questions": len(config_question_ids),
        }


class MockInterviewReportUsecase:
    @staticmethod
    def generate_behavioural_report(user, attempt):
        full_name = UserProfileRepository.get_user_fullname(user.id)
        eval_data = attempt.eval_data
        qualified = eval_data.get("qualified")
        total_score = eval_data.get("total_score")
        overall_summary = eval_data.get("overall_summary")
        total_emotion_score = eval_data.get("total_emotion_score")
        total_fluency_score = eval_data.get("total_fluency_score")
        total_coherence_score = eval_data.get("total_coherence_score")
        questions_evaluation_data = eval_data.get("questions_evaluation_data")
        status = attempt.status
        report = {
            "status": status,
            "qualified": qualified,
            "total_score": total_score,
            "overall_summary": overall_summary,
            "total_emotion_score": total_emotion_score,
            "total_fluency_score": total_fluency_score,
            "total_coherence_score": total_coherence_score,
            "questions_analysis": questions_evaluation_data,
        }

        return report
