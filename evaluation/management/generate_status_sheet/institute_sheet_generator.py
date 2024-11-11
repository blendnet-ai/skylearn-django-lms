from custom_auth.models import UserProfile
from django.conf import settings
from evaluation.models import Question
from evaluation.repositories import AssessmentAttemptRepository, QuestionRepository
from Feedback.repositories import FeedbackResponseRepository, FeedbackFormRepository
from custom_auth.services.custom_auth_service import CustomAuth
from InstituteConfiguration.repositories import InstituteRepository, QuestionListRepository
from ai_learning.repositories import DSAPracticeChatDataRepository
from custom_auth.repositories import UserProfileRepository
from evaluation.usecases import DSAReportUsecase, DashBoardDetailsUsecase
from datetime import datetime, timedelta
import logging
from django.contrib.auth import get_user_model
from evaluation.management.generate_status_sheet.utils import Utils
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper

User = get_user_model()
REGISTERED_STUDENTS_SHEET_NAME = "Registered Students"
STUDENTS_PROBLEMS_SOLVING_STATS_SHEET_NAME = "Students Problem Solving Statistics"
AGGREGATE_PROGRESS_SHEET_NAME = "Aggregate Progress"
DAILY_SHEET_NAME = "Daily Sheet"
INSTITUTE_WISE_BREAKUP_SHEET = "Institute Wise Breakup"
FEEDBACK_SHEET = "Feedback Sheet"
logger = logging.getLogger(__name__)
Custom_Auth_Service = CustomAuth


def fetch_all_data(name_of_institute=None):
    if name_of_institute:
        institute = InstituteRepository.get_institute_by_name(name_of_institute)
        problem_list = QuestionListRepository.get_question_list_by_institute_id(institute.id)
        users = UserProfileRepository.get_users_by_institute(institute)
        if problem_list is None:
            problem_list = QuestionRepository.return_questions_by_category(int(Question.Category.DSA_PRACTICE), None, [])
        else:
            problem_list = problem_list.get('question_ids')
        
    else:
        problem_list = QuestionRepository.return_questions_by_category(int(Question.Category.DSA_PRACTICE), None, [])
        users = UserProfileRepository.get_all_profiles().exclude(user_id_id=1)

    user_ids = users.values_list('user_id', flat=True)
    user_id_institute_map = {user.user_id.id: user.institute.name if user.institute else 'None' for user in users}
    user_id_name_map = {profile.user_id.id: profile.name for profile in users}
    user_id_phone_map = {user.user_id.id: user.phone for user in users}
    user_id_email_map = {user.user_id.id: user.user_id.email for user in users}

    assessment_attempts = AssessmentAttemptRepository.fetch_all_assessments_for_users(user_ids)
    question_ids = {attempt.question_list[0]["questions"][0] for attempt in assessment_attempts if attempt.question_list}
    questions = QuestionRepository.fetch_questions_by_ids(list(question_ids))
    question_tags_map = {question.id: question.tags for question in questions}
    question_difficulty_map = {question.id: question.question_data['difficulty'] for question in questions}
    question_company_map = {question.id: question.question_data['companies'] for question in questions}

    chat_sessions = DSAPracticeChatDataRepository.get_chat_sessions_for_assessments([attempt.assessment_id for attempt in assessment_attempts])
    chat_sessions_map = {session.assessment_attempt_id: session for session in chat_sessions}

    feedback_responses = FeedbackResponseRepository.get_feedback_responses_by_user_ids(user_ids)
    feedback_forms = {
        institute.id: FeedbackFormRepository.get_by_institute_id(institute.id)
        for institute in InstituteRepository.get_all()
        if institute.reporting_enabled
    }

    return {
        'users': users,
        'user_id_institute_map': user_id_institute_map,
        'user_id_name_map': user_id_name_map,
        'user_id_phone_map': user_id_phone_map,
        'user_id_email_map': user_id_email_map,
        'assessment_attempts': assessment_attempts,
        'problem_list':problem_list,
        'questions': questions,
        'question_tags_map': question_tags_map,
        'question_difficulty_map': question_difficulty_map,
        'question_company_map': question_company_map,
        'chat_sessions_map': chat_sessions_map,
        'feedback_responses': feedback_responses,
        'feedback_forms': feedback_forms
    }


def generate_institute_wise_breakup_sheet(data,global_sheet):
    sheet_data = []
    users = data['users']
    user_id_institute_map = data['user_id_institute_map']
    institutes = set(user_id_institute_map.values())
    
    for institute in institutes:
        institute_users = [user_id for user_id, institute_name in user_id_institute_map.items() if institute_name == institute]
        sheet_data.append({
            'Institute': institute,
            'Number of Users': len(institute_users),
        })
    
    return sheet_data

def generate_total_students_registered_sheet(data,global_sheet):
    users = data['users']
    problem_list =data['problem_list']
    user_ids = users.values_list('user_id', flat=True)
    user_attempts = data['assessment_attempts']

    # Determine active students
    active_students = [
        user_id for user_id in user_ids
        if any(attempt.created_at.date() >= (datetime.now() - timedelta(days=7)).date()
               for attempt in user_attempts if attempt.user_id.id == user_id)
    ]

    sheet_data_entry = {
        "Total Students Registered": len(users),
        "Total Problems In Bank": len(problem_list),
        "No of Active Students": len(active_students)
    }

    return [sheet_data_entry]

def generate_institute_wise_breakup_sheet(data,global_sheet):
    user_id_institute_map = data['user_id_institute_map']
    sheet_data = []
    institutes = set(user_id_institute_map.values())

    for institute in institutes:
        institute_users = [user_id for user_id, institute_name in user_id_institute_map.items() if institute_name == institute]
        sheet_data.append({
            'Institute': institute,
            'Number of Users': len(institute_users),
        })

    return sheet_data


def generate_student_problem_solving_status_sheet(data,global_sheet):
    users = data['users']
    user_id_name_map = data['user_id_name_map']
    assessment_attempts = data['assessment_attempts']
    question_tags_map = data['question_tags_map']
    user_id_institute_map = data['user_id_institute_map']

    assessment_attempts_map = {}
    for attempt in assessment_attempts:
        user_id = attempt.user_id
        if user_id not in assessment_attempts_map:
            assessment_attempts_map[user_id] = []
        assessment_attempts_map[user_id].append(attempt)

    sheet_data = []
    for user_id, attempts in assessment_attempts_map.items():
        submitted_attempts = [attempt for attempt in attempts if attempt.status == 2]
        total_problems_attempted = len(submitted_attempts)
        total_problems_solved = sum(1 for attempt in submitted_attempts if DashBoardDetailsUsecase._is_problem_solved(attempt))
        
        user_strengths = set()
        user_weaknesses = set()
        
        for attempt in submitted_attempts:
            question_id = attempt.question_list[0]["questions"][0] if attempt.question_list and attempt.question_list[0]["questions"] else None
            question_tags = question_tags_map.get(question_id, [])
            if DashBoardDetailsUsecase._is_problem_solved(attempt):
                user_strengths.update(question_tags)
            else:
                user_weaknesses.update(question_tags)
    
        user_weaknesses = ', '.join(user_weaknesses - user_strengths)
        user_strengths = ', '.join(user_strengths)
        last_login = Custom_Auth_Service.get_user_latest_login(user_id.username)

        data = {
            'User ID': user_id.id,
            'User Name': user_id_name_map[user_id.id],
            'User Email': user_id.email,
            'Total Problems Attempted': total_problems_attempted,
            'Total Problems Solved': total_problems_solved,
            'Strong topics': user_strengths,
            'Weak topics': user_weaknesses,
            'Last login': last_login
        }

        if global_sheet:
            data['College Name'] = user_id_institute_map[user_id.id]
        sheet_data.append(data)

    return sheet_data

def generate_daily_dsa_solving_sheet(data,global_sheet):
    users = data['users']
    user_id_name_map = data['user_id_name_map']
    assessment_attempts = data['assessment_attempts']
    question_tags_map = data['question_tags_map']
    question_difficulty_map = data['question_difficulty_map']
    question_company_map = data['question_company_map']
    chat_sessions_map = data['chat_sessions_map']
    user_id_institute_map = data['user_id_institute_map']

    sheet_data = []
    if user_id_institute_map:
        assessment_attempts = [
            attempt for attempt in assessment_attempts 
            if attempt.status == 2 or 
            (attempt.assessment_id in chat_sessions_map and chat_sessions_map.get(attempt.assessment_id).llm_chat_count > 0)
        ]
    else:
        assessment_attempts = [attempt for attempt in assessment_attempts if attempt.status == 2]

    for attempt in assessment_attempts:
        user_id = attempt.user_id
        question_id = attempt.question_list[0]["questions"][0] if attempt.question_list and attempt.question_list[0]["questions"] else None
        question_tags = question_tags_map.get(question_id, [])
        question_difficulty = question_difficulty_map.get(question_id, '')
        question_company = question_company_map.get(question_id, '')

        score = DSAReportUsecase.get_total_score(attempt.eval_data)
        time_taken = (attempt.updated_at - attempt.created_at).total_seconds()
        chat_session = chat_sessions_map.get(attempt.assessment_id)
        chat_count = chat_session.llm_chat_count if chat_session else 0

        data = {
            'User ID': user_id.id,
            'User Name': user_id_name_map[user_id.id],
            'User Email': user_id.email,
            'Date Time': attempt.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'Problem ID Attempted': question_id,
            'Difficulty': question_difficulty,
            'Topics': ', '.join(question_tags),
            'Company': question_company,
            'Score': score,
            'Time Taken in seconds': str(time_taken),
            'No. of Chat Messages': chat_count,
            'Assessment ID':attempt.assessment_id
        }

        if global_sheet:
            data['College Name'] = user_id_institute_map[user_id.id]
            data['Assessment Closed'] = 'Closed' if attempt.status == 2 else 'Not Closed'
            chat_history_link=settings.BACKEND_BASE_URL+f'/api/v1/evaluation/assessment-chat-history/{attempt.assessment_id}' if chat_count >0 else 'None'
            data['chat_history_link']=chat_history_link
        sheet_data.append(data)

    sheet_data = sorted(sheet_data, key=lambda x: x['Date Time'], reverse=True)
    return sheet_data

def generate_aggregate_level_sheet(data,global_sheet):
    users = data['users']
    assessment_attempts = data['assessment_attempts']

    # Collect dates from user registrations and assessment attempts
    dates = set(user.created_at.date() for user in users)
    dates.update(attempt.created_at.date() for attempt in assessment_attempts)

    # Iterate over each date and calculate the required metrics
    sheet_data = []
    for date in sorted(dates):
        student_registrations = len([user for user in users if user.created_at.date() == date])
        active_students = len([user for user in users if any(attempt.created_at.date() == date for attempt in assessment_attempts if attempt.user_id == user.user_id)])
        problems_attempted = len([attempt for attempt in assessment_attempts if attempt.created_at.date() == date and attempt.status == 2])

        today_attempts = [attempt for attempt in assessment_attempts if attempt.created_at.date() == date and attempt.status == 2]

        if today_attempts:
            successful_today_attempts = [attempt for attempt in today_attempts if DashBoardDetailsUsecase._is_problem_solved(attempt)]
            success_rate = len(successful_today_attempts) / len(today_attempts) * 100
            daily_scores = [DSAReportUsecase.get_total_score(attempt.eval_data) for attempt in today_attempts]
            avg_daily_score = sum(daily_scores) / len(daily_scores) if daily_scores else 0
        else:
            success_rate = 0
            avg_daily_score = 0

        sheet_data.append({
            'Date': date.strftime("%Y-%m-%d"),
            'Student Registration': student_registrations,
            'Active students': active_students,
            'Problems attempted': problems_attempted,
            'Success rate': success_rate,
            'Avg total score': avg_daily_score
        })

    # Sort the sheet data by date
    sheet_data = sorted(sheet_data, key=lambda x: x['Date'])
    
    return sheet_data

def generate_institute_wise_feedback(data,global_sheet):
    users = data['users']
    user_id_institute_map = data['user_id_institute_map']
    user_id_phone_map = data['user_id_phone_map']
    user_id_email_map = data['user_id_email_map']
    user_id_name_map = data['user_id_name_map']
    institutes = set(user_id_institute_map.values())
    institutes = list(filter(lambda x: x != 'None', institutes))
    sheet_data = []
    for institute in institutes:
        institute_users = [user_id for user_id, institute_name in user_id_institute_map.items() if institute_name == institute]
        institute_feedback = FeedbackResponseRepository.get_feedback_responses_by_user_ids(institute_users)

        # Get feedback form for the institute
        feedback_form = FeedbackFormRepository.get_by_institute_id(InstituteRepository.get_institute_by_name(institute).id)
        if feedback_form:
            columns = [field["label"] for section in feedback_form.data.get('sections') for field in section["fields"]]
        else:
            continue
        

        # Add data rows for each feedback
        for feedback in institute_feedback:
            user_id = feedback.user_id
            submitted_at=feedback.created_at
            phone_number = user_id_phone_map[user_id]
            email = user_id_email_map[user_id]
            name = user_id_name_map[user_id]
            assessment_id = feedback.assessment_id

            # Initialize the row with all columns set to None
            row = {column: None for column in columns}

            # Populate row data from feedback
            for section in feedback.data:
                for field in section.get("fields", []):
                    label = field.get("label")
                    if label in columns:
                        row[label] = field.get("value", None)
            
            row["Phone Number"] = phone_number
            row['Name']=name
            row['Institute']=institute
            row['Submitted At']=submitted_at
            row['Email']=email
            row["User ID"] = user_id
            row["Assessment ID"] = assessment_id
            sheet_data.append(row)
    
    sheet_data = sorted(sheet_data, key=lambda x: x['Assessment ID'], reverse=True)
    return sheet_data

def generate_institute_sheets():
    """
    Generates and updates sheets for each institute with their specific data.
    """
    all_institutes = InstituteRepository.get_all()
    for institute in all_institutes:
        if not institute.reporting_enabled:
            logger.info(f"Reporting not enabled for institute: {institute.name}")
            continue
        if not institute.reporting_sheet_id:
            logger.info(f"No reporting sheet ID for {institute.name}, skipping")
            continue

        institute_sheet_id = institute.reporting_sheet_id
        name_of_institute = institute.name
        data = fetch_all_data(name_of_institute=name_of_institute)
        new_spreadsheet_name = f"{name_of_institute} - {Utils.format_datetime(datetime.utcnow())}"
        
        registered_student_sheetdata=generate_total_students_registered_sheet(data,global_sheet=False)
        student_problem_solving_sheetdata=generate_student_problem_solving_status_sheet(data,global_sheet=False)
        aggregated_sheet_data=generate_aggregate_level_sheet(data,global_sheet=False)
        daily_solving_sheet_data=generate_daily_dsa_solving_sheet(data,global_sheet=False)

        gd_wrapper = GDWrapper(institute_sheet_id)

        gd_wrapper.update_sheet(REGISTERED_STUDENTS_SHEET_NAME, registered_student_sheetdata)
        gd_wrapper.update_sheet(STUDENTS_PROBLEMS_SOLVING_STATS_SHEET_NAME, student_problem_solving_sheetdata)
        gd_wrapper.update_sheet(AGGREGATE_PROGRESS_SHEET_NAME, aggregated_sheet_data)
        gd_wrapper.update_sheet(DAILY_SHEET_NAME, daily_solving_sheet_data)
        
        gd_wrapper.rename_spreadsheet(new_spreadsheet_name)


def generate_global_sheet():
    """
    Generates and updates sheets for each institute with their specific data.
    """
    new_spreadsheet_name = (
            f"Global DSA Sheet - {Utils.format_datetime(datetime.utcnow())}"
        )
    gd_wrapper = GDWrapper(settings.DSA_GLOBAL_SHEET_ID)
    data = fetch_all_data()
    all_institutes = InstituteRepository.get_all()

    feedback_data=generate_institute_wise_feedback(data,global_sheet=True)
    institute_wise_breakup=generate_institute_wise_breakup_sheet(data,global_sheet=True)
    registered_student_sheetdata=generate_total_students_registered_sheet(data,global_sheet=True)
    student_problem_solving_sheetdata=generate_student_problem_solving_status_sheet(data,global_sheet=True)
    aggregated_sheet_data=generate_aggregate_level_sheet(data,global_sheet=True)
    daily_solving_sheet_data=generate_daily_dsa_solving_sheet(data,global_sheet=True)

    gd_wrapper.update_sheet(REGISTERED_STUDENTS_SHEET_NAME, registered_student_sheetdata)
    gd_wrapper.update_sheet(STUDENTS_PROBLEMS_SOLVING_STATS_SHEET_NAME, student_problem_solving_sheetdata)
    gd_wrapper.update_sheet(AGGREGATE_PROGRESS_SHEET_NAME, aggregated_sheet_data)
    gd_wrapper.update_sheet(DAILY_SHEET_NAME, daily_solving_sheet_data)
    gd_wrapper.update_sheet(INSTITUTE_WISE_BREAKUP_SHEET,institute_wise_breakup)
    gd_wrapper.update_sheet(FEEDBACK_SHEET,feedback_data)

    gd_wrapper.rename_spreadsheet(new_spreadsheet_name)
