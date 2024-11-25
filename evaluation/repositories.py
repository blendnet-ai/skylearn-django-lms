import logging

from .models import Question, UserEvalQuestionAttempt, AssessmentAttempt, AssessmentGenerationConfig, DSAPracticeChatData, QuestionIssues,DSASheetsConfig, EventFlow
import datetime
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.exceptions import ValidationError
import os
from datetime import timedelta
logger = logging.getLogger(__name__)


class QuestionRepository:
    
    def fetch_question(question_id):
        question = Question.objects.filter(id=question_id).first()
        return question
    
    def return_questions_by_tag(category, num_questions, tag, selected_question_ids):
        questions = Question.objects.filter(category=category, tags__contains=[tag]).exclude(id__in=selected_question_ids).order_by('?')[:num_questions]
        return questions
    
    def return_questions_by_category(category, num_questions, selected_question_ids):
        questions = Question.objects.filter(category=category).exclude(id__in=selected_question_ids).order_by('?')[:num_questions]
        return questions
    
    def return_questions_by_sub_category(category, sub_category, num_questions, selected_question_ids):
        questions = Question.objects.filter(category=category, sub_category=sub_category).exclude(id__in=selected_question_ids).order_by('?')[:num_questions]
        return questions
    
    def fetch_questions_by_ids(question_ids):
        questions = Question.objects.filter(id__in=question_ids)
        return questions
    
    
class AssessmentGenerationConfigRepository:
        
    def return_assessment_generation_class_data(assessment_generation_id):
        # Sanchit-TODO: Should be get request here. Otherwise, DOESNOTEXIST error bubbles up like somethhing else.
        # Wherever fetching using id, by default it should be get request.
        assessment_data = AssessmentGenerationConfig.objects.get(assessment_generation_id = assessment_generation_id)
        return assessment_data
    
    
class AssessmentAttemptRepository:

    @staticmethod
    def fetch_assessment_from_report_id(report_id):
        assessment = AssessmentAttempt.objects.filter(report_id=report_id).first()
        return assessment
    
    @staticmethod
    def number_of_attempts_expired(*, assessment_generation_config_id, user_id):
        return AssessmentAttempt.objects.filter(assessment_generation_config_id=assessment_generation_config_id,
                                         user_id=user_id,status__in=[AssessmentAttempt.Status.EVALUATION_PENDING,
                                                                     AssessmentAttempt.Status.IN_PROGRESS,
                                                                     AssessmentAttempt.Status.COMPLETED]).count()

    def fetch_assessment_attempt(assessment_id):
        assessment = AssessmentAttempt.objects.get(assessment_id=assessment_id)
        return assessment

    def fetch_all_assessment_attempt(user_id):
        all_attempts = AssessmentAttempt.objects.filter(user_id=user_id).all()
        return all_attempts

    def fetch_assessment_configs():
        assessments_available = AssessmentGenerationConfig.objects.filter(enabled=True)
        return assessments_available

    def fetch_assessment_state(assessment_id, user_id):
        assessment_attempt = AssessmentAttempt.objects.filter(user_id=user_id, assessment_id=assessment_id).first()
        if not assessment_attempt:
            raise ValidationError("Assessment not found")
        
        if assessment_attempt.start_time is None:
            start_time = timezone.now()
            assessment_attempt.start_time = start_time
            assessment_attempt.save()

        question_list = assessment_attempt.question_list
        attempted_questions = UserEvalQuestionAttemptRepository.fetch_attempted_questions(assessment_attempt)
        
        time_left = (assessment_attempt.start_time + assessment_attempt.test_duration - timezone.now()).total_seconds()
        attempted_questions_data = []
        
        for attempt in attempted_questions:
            section = attempt.section
            mcq_answer = attempt.mcq_answer
            multiple_mcq_answer = attempt.multiple_mcq_answer
            answer_text = attempt.answer_text
            answer_audio_url = attempt.answer_audio_url
            question_id = attempt.question_id
            code_stubs=attempt.code_stubs
            attempted_questions_data.append({
                'question_id': question_id,
                'section': section,
                'mcq_answer': mcq_answer,
                'multiple_mcq_answer': multiple_mcq_answer,
                'answer_text': answer_text,
                'answer_audio_url': answer_audio_url,
                "code_stubs":code_stubs
            })
        
        assessment_status_resp = {
            'question_list': question_list,
            'attempted_questions': attempted_questions_data,
            'time_left': time_left if time_left > 0 else 0,
            'start_time': assessment_attempt.start_time,
            'test_duration': assessment_attempt.test_duration,
        }
        
        return assessment_status_resp
    
    def fetch_assessment_questions(assessment_id, user_id):
        assessment_questions = AssessmentAttempt.objects.filter(user_id=user_id, assessment_id=assessment_id).values('question_list','type').first()
        assessment_data = {
            'question_list': assessment_questions.get('question_list'),
            'type': assessment_questions.get('type'),
        }
        return assessment_data
    
    def fetch_user_assessment_history(user_id):
        assessment_history = AssessmentAttempt.objects.filter(user_id=user_id).filter(status__in = [AssessmentAttempt.Status.ABANDONED, AssessmentAttempt.Status.COMPLETED]).order_by('-start_time').values().all()
        return assessment_history

        
    def get_assessment_data(assessment_id, user_id):
        assessment_details = AssessmentAttempt.objects.filter(user_id=user_id, assessment_id=assessment_id).first()
        return assessment_details
    
    def add_or_update_assessment_attempt(assessment_attempt=None, assessment_generation_id= None, status=None, question_list=None, last_saved_section=None, last_saved=None, add_to_attempted_list=None, type = None, user = None, closed= None, test_duration = None, start_time = None, assessment_url = None, report_id = None, eval_data = None, evaluation_triggered=None, mode=None):
        if not assessment_attempt:
            assessment_attempt = AssessmentAttempt.objects.create(user_id=user, assessment_generation_config_id=assessment_generation_id, type=type, status=AssessmentAttempt.Status.IN_PROGRESS, test_duration=test_duration)

        if assessment_url is not None:
            assessment_attempt.assessment_url = assessment_url
        if report_id is not None:
            assessment_attempt.report_id = report_id
        if last_saved_section is not None:
            assessment_attempt.last_saved_section = last_saved_section
        if status is not None:
            assessment_attempt.status = status
        if question_list is not None:
            assessment_attempt.question_list = question_list
        if last_saved is not None:
            assessment_attempt.last_saved = last_saved
        if add_to_attempted_list is not None:
            assessment_attempt.attempted_list.append(add_to_attempted_list)
        if closed is not None:
            assessment_attempt.closed = closed
        if test_duration is not None:
            assessment_attempt.test_duration = test_duration
        if start_time is not None:
            assessment_attempt.start_time = start_time
        if eval_data is not None:
            assessment_attempt.eval_data = eval_data
        if evaluation_triggered is not None:
            assessment_attempt.evaluation_triggered = evaluation_triggered
        if mode is not None:
            assessment_attempt.mode = mode
        assessment_attempt.save()

        return assessment_attempt.assessment_id

    def fetch_all_assessment_attempts(user_id):
        latest_assessment_attempts = (AssessmentAttempt.objects
            .filter(user_id=user_id, status = int(AssessmentAttempt.Status.COMPLETED))
            .order_by('type', '-start_time')
            .exclude(start_time__isnull=True)
            .distinct('type')
        )
        return latest_assessment_attempts
    
    def fetch_all_assessments_completed(user_id):
        completed_assessment_attempts = (AssessmentAttempt.objects
            .filter(user_id=user_id, type=4, status = int(AssessmentAttempt.Status.COMPLETED))
            .order_by('type', '-start_time')
        )
        return completed_assessment_attempts

    def does_attempts_exist_for_date(updated_date: timezone.datetime):
        date_to_check = updated_date.date() if isinstance(updated_date, timezone.datetime) else updated_date

        exists = AssessmentAttempt.objects.filter(
            status=AssessmentAttempt.Status.COMPLETED,
            updated_at__date=date_to_check
        ).exists()

        return exists

    def fetch_all_assessments_for_users(user_ids):
        assessments = AssessmentAttempt.objects.filter(user_id__in=user_ids,type=int(Question.Category.DSA_PRACTICE)).all()
        return assessments

    def update_assessment_time(assessment_id, updated_timestamp):
        obj = AssessmentAttempt.objects.filter(
            assessment_id=assessment_id,
            type=int(Question.Category.DSA_PRACTICE)
        ).first()
        
        if obj:
            obj.updated_at = updated_timestamp
            obj.save()
        else:
            logging.info(f"No AssessmentAttempt found with assessment_id {assessment_id} and type {Question.Category.DSA_PRACTICE}")



    
class UserEvalQuestionAttemptRepository:
    
    def fetch_attempted_questions(assessment_attempt):
        attempted_questions = UserEvalQuestionAttempt.objects.filter(assessment_attempt_id=assessment_attempt.assessment_id, status__in = [UserEvalQuestionAttempt.Status.ATTEMPTED, UserEvalQuestionAttempt.Status.EVALUATING]).all()
        return attempted_questions
    
    def fetch_evaluated_questions(assessment_attempt):
        attempted_questions = UserEvalQuestionAttempt.objects.filter(assessment_attempt_id=assessment_attempt.assessment_id, status__in = [UserEvalQuestionAttempt.Status.EVALUATED]).all()
        return attempted_questions
    
    def create_user_question_attempt(user, question_id, assessment_attempt_id):
        user_attempt, _ = UserEvalQuestionAttempt.objects.get_or_create(
            user_id=user,
            question_id=question_id,
            assessment_attempt_id=assessment_attempt_id
        )
        return user_attempt

    def save_user_question_attempt(user_question_attempt, mcq_answer=None, multiple_mcq_answer=None, answer_text=None, answer_audio_url = None, code=None, code_stubs=None, section=None, status=None):
        if multiple_mcq_answer is not None:
            user_question_attempt.multiple_mcq_answer = multiple_mcq_answer
        if mcq_answer is not None:
            user_question_attempt.mcq_answer = mcq_answer
        if status is not None:
            user_question_attempt.status = status
        if answer_text is not None:
            user_question_attempt.answer_text = answer_text
        if section is not None:
            user_question_attempt.section = section
        if answer_audio_url is not None:
            user_question_attempt.answer_audio_url = answer_audio_url
        if code is not None:
            user_question_attempt.code = code
        if code_stubs is not None:
            user_question_attempt.code_stubs = code_stubs
        user_question_attempt.save()
        
    def fetch_user_question_attempt(user, question_id, assessment_attempt):
        user_attempt = UserEvalQuestionAttempt.objects.filter(user_id=user.id, question_id=question_id, assessment_attempt_id = assessment_attempt.assessment_id).first()
        return user_attempt
        
    def fetch_user_question_attempt_from_id(user, user_question_attempt_id, assessment_attempt):
        user_attempt = UserEvalQuestionAttempt.objects.filter(user_id=user.id, id=user_question_attempt_id, assessment_attempt_id = assessment_attempt.assessment_id).first()
        return user_attempt
  
class AudioURLProvider:
    @staticmethod
    def get_storage_container_name():
        """ Returns the container name """
        CONTAINER_NAME = "speaking-audios"
        return CONTAINER_NAME

class DSAPracticeChatDataRepository:
    @staticmethod
    def get_chat_data(user_id, question_id, assessment_attempt_id):
        return DSAPracticeChatData.objects.get(
            user_id=user_id,
            question__id=question_id,
            assessment_attempt__assessment_id=assessment_attempt_id,
        )

class QuestionIssuesRepository:
    @staticmethod
    def save_question_issue(user,type_of_issue,question_id,assessment_attempt_id,description):
        question_issue=QuestionIssues.objects.create(
            user_id=user,
            type_of_issue=type_of_issue,
            question_id=question_id,
            assessment_attempt_id=assessment_attempt_id,
            description=description)
        return question_issue.id

class DSASheetConfigRepository:

    @staticmethod
    def get_all_configs():
        return [{"name":config.name,"id":config.id} for config in DSASheetsConfig.objects.all()]
    
    @staticmethod
    def get_config_questions_list(name):
        try:
            config = DSASheetsConfig.objects.get(name=name)
            return config.question_ids
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_config_questions_list_by_id(id:int):
        config = DSASheetsConfig.objects.get(id=id)
        return config.question_ids

class EventFlowRepository:
    @staticmethod
    def get_event_flows_for_assessment_ids(assessment_ids):
        return EventFlow.objects.filter(root_arguments__assessment_attempt_id__in=assessment_ids)
