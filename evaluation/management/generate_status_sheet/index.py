import datetime

from django.conf import settings
from custom_auth.models import UserProfile
from data_repo.models import ConfigMap
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper
from evaluation.management.generate_status_sheet.utils import Utils
from evaluation.models import AssessmentAttempt
from django.contrib.auth import get_user_model
from services.resume_builder_service import ResumeBuilderService

User = get_user_model()


def get_attempts_sheet_entries(start_date):
    attempts = AssessmentAttempt.objects.filter(
        start_time__gte=start_date
    ).order_by("-start_time")

    attempts_sheet = []

    if attempts:
        for attempt in attempts:
            start_time = attempt.start_time
            formatted_start_time = Utils.format_datetime(start_time)

            for choice in AssessmentAttempt.Type.choices:
                if int(choice[0]) == int(attempt.type):
                    type_label = choice[1]
                    break

            for choice in AssessmentAttempt.Status.choices:
                if int(choice[0]) == int(attempt.status):
                    status_label = choice[1]
                    break

            eval_data = attempt.eval_data

            if attempt.type == int(AssessmentAttempt.Type.PERSONALITY):
                score = eval_data.get("score_text", "N/A")
            else:
                score = str(eval_data.get("percentage", "N/A"))

            attempts_sheet_entry = {
                "email": attempt.user_id.email,
                "status": status_label,
                "score": score,
                "type": type_label,
                "start_time": formatted_start_time,
                "user_id": attempt.user_id.id,
                "assessment_id": attempt.assessment_id,
            }

            attempts_sheet.append(attempts_sheet_entry)
    return attempts_sheet


def get_users_sheet_entries(start_date):

    users = User.objects.filter(
        assessmentattempt__start_time__gte=start_date,
        date_joined__gte=start_date
    ).distinct()

    email_list = list(users.values_list('email', flat=True))

    users_sheet = []
    resume_data=ResumeBuilderService().get_all_reumses(user_id=settings.ADMIN_FIREBASE_ACCOUNT_ID,email_list=email_list)
    if users:
        for user in users:
            user_id = user.id

            attempts = AssessmentAttempt.objects.filter(user_id=int(user_id)).order_by(
                "-start_time"
            )

            try:
                user_profile = UserProfile.objects.get(user_id=int(user_id))
            except UserProfile.DoesNotExist:
                user_profile = None

            user_resume_data = [resume for resume in resume_data if resume["email"] == user.email]
            user_resume = user_resume_data[0]['resumes'] if user_resume_data else []
            no_of_resumes=len(user_resume)
            institute_name = ""
            if user_profile and user_profile.form_response:
                institute_name=user_profile.form_response.get("college")
            users_sheet_entry = {
                "email": user.email,
                "user_id": user_id,
                "cv_score": user_profile.cv_score if user_profile else "",
                "cv_details": user_profile.cv_details if user_profile else "",
                "form_response": user_profile.form_response if user_profile else "",
                "institute_name":institute_name,
                "no_of_resumes": no_of_resumes,
                "resumes": user_resume,
            }

            most_recent_attempts, attempt_counts = (
                Utils.get_most_recent_completed_attempts(list(attempts))
            )

            for choice in AssessmentAttempt.Type.choices:
                test_type = int(choice[0])
                test_type_label = choice[1]
                attempt = None

                if most_recent_attempts:
                    attempt = most_recent_attempts.get(test_type)
                if attempt is None:
                    attempt_count = 0
                    score = "N/A"
                    formatted_start_time = "N/A"
                else:
                    attempt_count = attempt_counts.get(test_type)
                    eval_data = attempt.eval_data

                    if test_type == int(AssessmentAttempt.Type.PERSONALITY):
                        score = eval_data.get("score_text", "N/A")
                    else:
                        score = str(eval_data.get("percentage", "N/A"))

                    start_time = attempt.start_time
                    formatted_start_time = Utils.format_datetime(start_time)

                users_sheet_entry[f"{test_type_label} - attempts"] = attempt_count
                users_sheet_entry[f"{test_type_label} - score"] = score
                users_sheet_entry[f"{test_type_label} - start_time"] = (
                    formatted_start_time
                )

            users_sheet.append(users_sheet_entry)
        return users_sheet


def generate_status_sheets():
    new_speadsheet_name = (
        f"evaluation - {Utils.format_datetime(datetime.datetime.utcnow())}"
    )

    gd_wrapper = GDWrapper(settings.SPEADSHEET_ID)

    start_date = datetime.datetime(2024, 7, 10)

    tests_sheet = get_attempts_sheet_entries(start_date)
    gd_wrapper.update_sheet(settings.TESTS_SUBSHEET_NAME, tests_sheet)

    users_sheet = get_users_sheet_entries(start_date)
    gd_wrapper.update_sheet(settings.USERS_SUBSHEET_NAME, users_sheet)

    gd_wrapper.rename_spreadsheet(new_speadsheet_name)
