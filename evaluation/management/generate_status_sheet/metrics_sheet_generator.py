from custom_auth.models import UserProfile
from django.conf import settings
from evaluation.models import Question
from evaluation.repositories import AssessmentAttemptRepository,EventFlowRepository
from custom_auth.services.custom_auth_service import CustomAuth
from InstituteConfiguration.repositories import InstituteRepository, QuestionListRepository
from ai_learning.repositories import DSAPracticeChatDataRepository
from custom_auth.repositories import UserProfileRepository
from django.contrib.auth import get_user_model
from datetime import date, datetime, timedelta
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper
from evaluation.management.generate_status_sheet.utils import Utils
import logging

User = get_user_model()

REPORT_METRICS_SHEET_NAME = "DSA Assessment Report Metrics"
AI_CHAT_METRICS_SHEET_NAME = "AI Chat Metrics"
CODE_COMPILE_METRICS_SHEET_NAME = "Complile Duration Metrics"

logger = logging.getLogger(__name__)
Custom_Auth_Service=CustomAuth


def get_users_and_assessment_attempts():
    users = UserProfileRepository.get_all_profiles()
    user_ids = users.values_list('user_id', flat=True)
    assessment_attempts = AssessmentAttemptRepository.fetch_all_assessments_for_users(user_ids)
    return users, assessment_attempts

def generate_timetaken_for_report_sheet(users, assessment_attempts):
    successful_attempts = [attempt.assessment_id for attempt in assessment_attempts if attempt.status == 2]
    data = EventFlowRepository.get_event_flows_for_assessment_ids(successful_attempts)
    sheet_data = []
    for event_flow in data:
        assessment_id = event_flow.root_arguments.get('assessment_attempt_id')
        time_required_for_report = event_flow.run_duration
        sheet_data.append({
            'assessment id': assessment_id,
            'time required for report': str(time_required_for_report)
        })
    return sheet_data

def generate_code_compile_duration_sheet(users, assessment_attempts):
    attempt_ids = [attempt.assessment_id for attempt in assessment_attempts]
    chat_sessions = DSAPracticeChatDataRepository.get_chat_sessions_for_assessments(attempt_ids)
    sheet_data = []
    for session in chat_sessions:
        assessment_id = session.assessment_attempt_id
        compile_duration = session.compile_duration_logs[-1].get('duration') if len(session.compile_duration_logs)>0 else None
        submit_duration = session.submit_compile_log.get('duration') if len(session.submit_compile_log)>0 else None
        row_data = {
            'assessment id': assessment_id,
            'compile duration': compile_duration,
            'submit duration': submit_duration
        }
        sheet_data.append(row_data)
    return sheet_data

def generate_timetaken_for_chat_messages_sheet(users, assessment_attempts):
    attempt_ids = [attempt.assessment_id for attempt in assessment_attempts]
    chat_sessions = DSAPracticeChatDataRepository.get_chat_sessions_for_assessments(attempt_ids)
    sheet_data = []
    for session in chat_sessions:
        assessment_id = session.assessment_attempt_id
        sheet_data.extend(
            {
                'assessment id': assessment_id,
                'response from bot': chat.get('content'),
                'message generation time in seconds': chat.get('message_generation_time',None)
            }
            for chat in session.llm_chat_history
            if chat.get('role') == 'assistant'
        )
    return sheet_data

def generate_metrics_sheet():
    users, assessment_attempts = get_users_and_assessment_attempts()
    report_metrics_sheet = generate_timetaken_for_report_sheet(users, assessment_attempts)
    AI_chat_metrics_sheet = generate_timetaken_for_chat_messages_sheet(users, assessment_attempts)
    compile_generation_metrics_sheet = generate_code_compile_duration_sheet(users, assessment_attempts)

    gd_wrapper = GDWrapper(settings.DSA_METRICS_SHEET_ID)
    gd_wrapper.update_sheet_for_new_data(REPORT_METRICS_SHEET_NAME, report_metrics_sheet)
    gd_wrapper.update_sheet_for_new_data(AI_CHAT_METRICS_SHEET_NAME, AI_chat_metrics_sheet)
    gd_wrapper.update_sheet_for_new_data(CODE_COMPILE_METRICS_SHEET_NAME, compile_generation_metrics_sheet)

    new_spreadsheet_name = (
        f"DSA Assessment Technical Metrics Sheet - {Utils.format_datetime(datetime.utcnow())}"
    )
    gd_wrapper.rename_spreadsheet(new_spreadsheet_name)


