from django.contrib.auth import get_user_model
from config import settings
from course.repositories import CourseRepository, BatchRepository
from events_logger.repositories import PageEventRepository
from accounts.repositories import StudentRepository, CourseProviderRepository
from custom_auth.repositories import UserProfileRepository
from meetings.repositories import AttendaceRecordRepository
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper
from evaluation.management.generate_status_sheet.utils import Utils
from reports.repositories import UserCourseReportRepository, DailyAggregationRepository
from accounts.usecases import StudentProfileUsecase
from evaluation.repositories import AssessmentAttemptRepository, AssessmentGenerationConfigRepository
from evaluation.models import AssessmentGenerationConfig
from Feedback.repositories import FeedbackResponseRepository
import json
from datetime import datetime

User = get_user_model()
# Optimized function to get all required data at once
def fetch_all_required_data():
    date = datetime.now().date()
    excluded_emails = settings.TEST_EMAILS

    # Fetch all students
    students = StudentRepository.get_all_students()
    user_ids = [student.student.id for student in students]
    email_map = {student.student.id: student.student.email for student in students}

    feedback_responses = FeedbackResponseRepository.get_feedback_responses_by_user_ids(user_ids)
    user_profiles = UserProfileRepository.get_all_profiles_for_user_ids(user_ids)
    courses = CourseRepository.get_all_courses()
    batches = BatchRepository.get_all_batches()

    activity_data = DailyAggregationRepository.get_aggregations_by_date(date)
    meetings_data = AttendaceRecordRepository.get_attendance_records_by_date(date)
    assessments_data = AssessmentAttemptRepository.fetch_assessments_attempts_data_by_date(date)
    course_providers_data = CourseProviderRepository.get_all_course_providers()

    # Maps for quick lookup
    user_profiles_map = {profile.user_id_id: profile for profile in user_profiles}
    course_map = {course.get('id'): course for course in courses}
    batch_map = {batch.id: batch for batch in batches}

    # Build user_course_batch_map
    user_course_batch_map = {}
    for student in students:
        batches_for_student = list(student.batches.all())
        user_course_batch_map[student.student.id] = []

        for batch in batches_for_student:
            if batch.id in batch_map:
                course = batch_map[batch.id].course
                user_course_batch_map[student.student.id].append({
                    "course_name": course.title,
                    "batch_id": batch.id,
                    "course_id": course.id,
                    "course_provider_id": course.course_provider_id,
                    "enrolled date": batch.created_at
                })
    reports_data = UserCourseReportRepository.get_reports_data()
    # Filtering if ECF
    if settings.DEPLOYMENT_TYPE == "ECF":
        filtered_students = [s for s in students if s.student.email not in excluded_emails]
        filtered_user_ids = {s.student.id for s in filtered_students}
        filtered_user_profiles_map = {
            uid: profile for uid, profile in user_profiles_map.items() if uid in filtered_user_ids
        }
        filtered_feedback_responses = [
            fr for fr in feedback_responses if fr.user_id in filtered_user_ids
        ]
        filtered_user_course_batch_map = {
            uid: data for uid, data in user_course_batch_map.items() if uid in filtered_user_ids
        }

        filtered_activity_data = [
            a for a in activity_data if a.user_id in filtered_user_ids
        ]
        filtered_meetings_data = [
            m for m in meetings_data if m.user_id_id in filtered_user_ids
        ]
        filtered_assessments_data = [
            a for a in assessments_data if a.user_id_id in filtered_user_ids
        ]
        filtered_reports_data=[
            r for r in reports_data if r.user_id in filtered_user_ids
        ]
    else:
        filtered_students = students
        filtered_user_profiles_map = user_profiles_map
        filtered_feedback_responses = feedback_responses
        filtered_user_course_batch_map = user_course_batch_map
        filtered_activity_data = activity_data
        filtered_meetings_data = meetings_data
        filtered_assessments_data = assessments_data
        filtered_reports_data=reports_data

    return {
        'students': students,
        'user_profiles_map': user_profiles_map,
        'course_map': course_map,
        'batch_map': batch_map,
        'user_course_batch_map': user_course_batch_map,
        'activity_data': activity_data,
        'meetings_data': meetings_data,
        'assessments_data': assessments_data,
        'course_providers_data': course_providers_data,
        'feedback_responses': feedback_responses,
        'reports_data':reports_data,

        # Filtered values
        'filtered_students': filtered_students,
        'filtered_user_profiles_map': filtered_user_profiles_map,
        'filtered_feedback_responses': filtered_feedback_responses,
        'filtered_user_course_batch_map': filtered_user_course_batch_map,
        'filtered_activity_data': filtered_activity_data,
        'filtered_meetings_data': filtered_meetings_data,
        'filtered_assessments_data': filtered_assessments_data,
        'filtered_reports_data':filtered_reports_data
    }

def populate_course_provider_sheet(data):
    course_providersdata=data['course_providers_data']
    final_data=[]
    for data in course_providersdata:
        final_data.append({'CourseProviderId':data.id,'CourseProviderName':data.name})
    return final_data

# Function for Sheet 1 - Populate user data
def populate_lms_users_reporting_data(data):
    student_data = []
    for user_id, user_profile in data['user_profiles_map'].items():
        user = user_profile.user_id
        # Get list of course info for this user
        course_info_list = data['user_course_batch_map'].get(user.id, [])
        
        # Create base user info
        base_user_info = {
            "StudentID": user.id,
            "First Name": user.first_name,
            "Last Name": user.last_name,
            "Full Name": UserProfileRepository.fetch_value_from_form('name', user_profile.user_data),
            "Email": user.email,
            "Phone": user_profile.phone if user_profile.phone else UserProfileRepository.fetch_value_from_form('Phone', user_profile.user_data),  # From UserProfile,
            'Project': UserProfileRepository.fetch_value_from_form('project', user_profile.user_data),
            "DOB": UserProfileRepository.fetch_value_from_form('dob', user_profile.user_data),
            "Gender": UserProfileRepository.fetch_value_from_form('gender', user_profile.user_data),
            'Department': UserProfileRepository.fetch_value_from_form('department', user_profile.user_data),
            "College": UserProfileRepository.fetch_value_from_form('College Name', user_profile.user_data),
            "State": UserProfileRepository.fetch_value_from_form('State', user_profile.user_data),
            "District": UserProfileRepository.fetch_value_from_form('District', user_profile.user_data),
        }

        if course_info_list:
            # Create an entry for each course the student is enrolled in
            for course_info in course_info_list:
                entry = base_user_info.copy()
                entry.update({
                    "Course Name": course_info.get("course_name"),
                    "Course ID": course_info.get("course_id"),
                    "Course Provider ID":course_info.get("course_provider_id"),
                    "Batch ID": course_info.get("batch_id"),
                    "Enrollment DateTIme": course_info.get("enrolled date")
                })
                student_data.append(entry)
        else:
            # If no courses, add entry with None for course fields
            entry = base_user_info.copy()
            entry.update({
                "Course Name": None,
                "Course ID": None,
                "Batch ID": None,
                "Course Provider ID":None,
                "Enrolled Date": None
            })
            student_data.append(entry)

    return student_data


def populate_lms_batch_reporting_data(data):
    batch_data = []
    for batch_id, batch in data['batch_map'].items():
        batch_data.append({
            "Batch ID": batch.id,
            "Course ID": batch.course_id,
            "Course Provider ID":batch.course.course_provider_id,
            "Course Name": batch.course.title,
            "Start Date": batch.created_at.date(),
            "Number of Students": len(batch.students)
        })
    return batch_data

def populate_AFH_reporting_data(data):
    profile_data = []
    for user_id, user_profile in data['user_profiles_map'].items():
        user = user_profile.user_id
        dob_value = UserProfileRepository.fetch_value_from_form('dob', user_profile.user_data)
        # Get list of course info for this user
        course_info_list = data['user_course_batch_map'].get(user.id, [])
        
        # Create base user info
        base_profile_info = {
            "Beneficiary ID (Full Adhaar Number)": UserProfileRepository.fetch_value_from_form('beneficiaryId', user_profile.user_data),
            "Enrollment Date (DD/MM/YY)": None,
            "Name": user.get_full_name,
            "Age": StudentProfileUsecase._calculate_age(user_profile.user_data),
            "Gender": UserProfileRepository.fetch_value_from_form('gender', user_profile.user_data),
            "Contact (10-Digit)": user_profile.phone if user_profile.phone else UserProfileRepository.fetch_value_from_form('Phone', user_profile.user_data),  # From UserProfile,
            "State": UserProfileRepository.fetch_value_from_form('State', user_profile.user_data),
            "District": UserProfileRepository.fetch_value_from_form('District', user_profile.user_data),
            "College Name": UserProfileRepository.fetch_value_from_form('College Name', user_profile.user_data),
            "Highest Qualification": UserProfileRepository.fetch_value_from_form('highestQualification', user_profile.user_data),
            "Annual Income in INR": UserProfileRepository.fetch_value_from_form('annualIncome', user_profile.user_data),
            "Center Name": UserProfileRepository.fetch_value_from_form('Center Name', user_profile.user_data) or UserProfileRepository.fetch_value_from_form('Centre Name', user_profile.user_data),
            "Training Location District Name": UserProfileRepository.fetch_value_from_form('Training Location District Name', user_profile.user_data),
            "Training Location City Name": UserProfileRepository.fetch_value_from_form('Training Location City Name', user_profile.user_data),
            "Date of Birth (DD/MM/YY)": datetime.strptime(str(dob_value), '%Y-%m-%d').strftime('%d/%m/%y') if dob_value else None,
            "Email ID": user.email,
            "Parent/Guardian Name": UserProfileRepository.fetch_value_from_form('parentGuardianName', user_profile.user_data),
            "Parent/Guardian Phone Number": UserProfileRepository.fetch_value_from_form('parentGuardianPhone', user_profile.user_data),
            "Parent / Guardian Occupation": UserProfileRepository.fetch_value_from_form('parentGuardianOccupation', user_profile.user_data),
            "Beneficiary Work Experience (in Years)": UserProfileRepository.fetch_value_from_form('workExperience', user_profile.user_data),
            "Enrollment Status": UserProfileRepository.fetch_value_from_form('Enrollment Status', user_profile.user_data),
            "Course ID": None,
            "Course Name": None,
            "Batch ID": None,
            "Onboarding Source":UserProfileRepository.fetch_value_from_form('Onboarding Source', user_profile.user_data),
            "PWD (Status)": UserProfileRepository.fetch_value_from_form('pwdStatus', user_profile.user_data),
            "Is a family member govt. employee?": UserProfileRepository.fetch_value_from_form('isFamilyMemberGovtEmployee', user_profile.user_data),

        }

        if course_info_list:
            # Create an entry for each course the student is enrolled in
            for course_info in course_info_list:
                entry = base_profile_info.copy()
                entry.update({
                    "Course Name": course_info.get("course_name"),
                    "Course ID": course_info.get("course_id"),
                    # "Course Provider ID":course_info.get("course_provider_id"),
                    "Batch ID": course_info.get("batch_id"),
                    "Enrollment Date (DD/MM/YY)":  course_info.get("enrolled date").date().strftime("%d/%m/%y")
                })
                profile_data.append(entry)

        else:
            # If no courses, add entry with None for course fields
            entry = base_profile_info.copy()
            entry.update({
                "Course Name": None,
                "Course ID": None,
                # "Course Provider ID":None,
                "Batch ID": None,
                "Enrollment Date (DD/MM/YY)": None
            })
            profile_data.append(entry)


    return profile_data

def populate_course_provider_reporting_data(data):
    final_data = []
    reports_data=data['reports_data']
    for report in reports_data:
        user_profile = data['user_profiles_map'].get(report.user_id)
        course_info_list = data['user_course_batch_map'].get(report.user_id, [])
        course_info =  next((info for info in course_info_list if info['course_id'] == report.course_id), {})
        user = report.user  # User object is accessible directly from the report
        final_data.append({
            'Student ID': user.id,
            'First Name': user.first_name,  # From User model
            'Last Name': user.last_name,  # From User model
            'Project': UserProfileRepository.fetch_value_from_form('project', user_profile.user_data),
            'DOB': UserProfileRepository.fetch_value_from_form('dob', user_profile.user_data),
            'Gender': UserProfileRepository.fetch_value_from_form('gender', user_profile.user_data),
            'Email': user.email,  # From User model
            'Phone Number': user_profile.phone if user_profile.phone else UserProfileRepository.fetch_value_from_form('Phone', user_profile.user_data),  # From UserProfile
            'Department': UserProfileRepository.fetch_value_from_form('department', user_profile.user_data),
            'State': UserProfileRepository.fetch_value_from_form('State', user_profile.user_data),
            'District': UserProfileRepository.fetch_value_from_form('District', user_profile.user_data),
            'Course Name': course_info.get("course_name"),
            "Course Provider ID":course_info.get("course_provider_id"),
            'Batch ID': course_info.get("batch_id"),
            'Time Spent on Assessments (in mins)':round(report.assessment_time.total_seconds()/60), 
            'Time Spent on Videos (in mins)': round(report.resource_time_video.total_seconds()/60),
            'Time Spent on Reading (in mins)': round(report.resource_time_reading.total_seconds()/60),
            'Time Spent on Recordings (in mins)': round(report.time_spent_in_recording_classes.total_seconds()/60),
            'Time Spent in Live Classes (in mins)': round(report.time_spent_in_live_classes.total_seconds()/60),
            'Total Learning Time (in mins)': round(report.total_time_spent.total_seconds()/60),
            'Number of classes attended': report.classes_attended,
            'Number of classes missed': report.total_classes - report.classes_attended,
            'Attendance %': (report.classes_attended / (report.classes_attended + (report.total_classes - report.classes_attended))) * 100 if report.total_classes else 0
        })
    return final_data

def populate_lms_time_spent_reporting_data(data):
    final_data = []
    reports_data = data['reports_data']

    for report in reports_data:
        user_profile = data['user_profiles_map'].get(report.user_id)
        course_info_list = data['user_course_batch_map'].get(report.user_id, [])
        course_info =  next((info for info in course_info_list if info['course_id'] == report.course_id), {})
        user = report.user  # User object is accessible directly from the report
        final_data.append({
            'Student ID': user.id,
            "Email": user.email,
            "Phone Number": user_profile.phone if user_profile.phone else UserProfileRepository.fetch_value_from_form('Phone', user_profile.user_data),  # From UserProfile
            'Course ID': course_info.get("course_id"),
            "Course Provider ID":course_info.get("course_provider_id"),
            'Batch ID': course_info.get("batch_id"),  
            'Time Spent on Assessments (in mins)':round(report.assessment_time.total_seconds()/60),          
            'Time Spent on Videos (in mins)': round(report.resource_time_video.total_seconds()/60), 
            'Time Spent on Reading (in mins)': round(report.resource_time_reading.total_seconds()/60),
            'Time Spent on Recordings (in mins)': round(report.time_spent_in_recording_classes.total_seconds()/60),
            'Time Spent in Live Classes (in mins)': round(report.time_spent_in_live_classes.total_seconds()/60),
            'Total Learning Time (in mins)': round(report.total_time_spent.total_seconds()/60),
            'Number of classes attended': report.classes_attended,
            'Number of classes missed': report.total_classes - report.classes_attended
        })
    return final_data

def populate_lms_activity_logs_data(data):
    activities=data['activity_data']
    user_course_batch_map=data['user_course_batch_map']
    final_data=[]
    
    for activity in activities:
        user_course_data=next((entry for entry in user_course_batch_map.get(activity.user_id, []) if entry['course_id'] == activity.course_id), None)
        batch_id=user_course_data.get('batch_id') if user_course_data else None
        final_data.append({
            'Student ID':activity.user_id,
            'Batch ID': batch_id,
            'Resource ID': activity.reference_id,
            'Resource Name':activity.resource_name,
            'Resource Type':activity.type_of_aggregation,
            'Accessed On':activity.date,
            'Duration':activity.time_spent
            
        })
    return final_data

def populate_lms_live_classes_logs_data(data):
    meetings_data=data['meetings_data']
    final_data=[]
    for record in meetings_data:
        meeting = record.meeting 
        series = meeting.series
        final_data.append({
            'Student ID': record.user_id_id,
            'Batch ID':series.course_enrollments.first().batch_id, 
            'Class ID':meeting.id,
            'Date Time':meeting.start_time,
            'Class Duration':meeting.duration,
            'Attendance':record.attendance
        })
    return final_data

def populate_lms_assessments_logs_data(data):
    assessments_data = data['assessments_data']
    final_data = []
    for record in assessments_data:
        # Get the assessment type
        assessment_type = record.assessment_generation_config_id.assessment_type
        # Initialize the grade/score and comments
        grade_or_score = None
        comments = ''
        total_score=None
        max_score=None
        percentage=None
        # Check if eval_data exists and get the percentage or total_score
        if record.eval_data:
            percentage = record.eval_data.get('percentage')
            max_score=record.eval_data.get('max_score')
            total_score=record.eval_data.get('total_score')
            if int(assessment_type) == int(AssessmentGenerationConfig.Type.Qualitative):
                # Determine the grade based on percentage
                if percentage is not None:
                    if percentage < 30:
                        grade_or_score = 'Beginner'
                    elif percentage < 60:
                        grade_or_score = 'Intermediate'
                    else:
                        grade_or_score = 'Advanced'
                else:
                    grade_or_score = 'N/A'  # or some default value if percentage is not available
            
            elif assessment_type == int(AssessmentGenerationConfig.Type.Quantitative):
                # Use the total score for quantitative assessments
                grade_or_score = percentage
        
        # Append the final data for each record
        final_data.append({
            'Student ID': record.user_id_id,
            'Assessment ID': record.assessment_id,
            'DateTime': record.updated_at,
            'Assessment Type': assessment_type,
            'Percentage': grade_or_score,
            'Total Score':total_score,
            'Max Score':max_score,
            'Report Link': None,
            'Comments': comments
        })
    return final_data

def populate_lms_feedback_responses_data(data):
    
    final_data = []
    feedback_responses=data['feedback_responses']
    for response in feedback_responses:
        user_profile = data['user_profiles_map'].get(response.user_id)
        user = user_profile.user_id if user_profile else None
        
        response_data = {
            'Student ID': response.user_id,
            'Student Name': user.get_full_name if user else None,
            'Student Email': user.email if user else None,
            'Batch ID': response.course_feedback_entry.batch_id,
            'Submitted Date': response.created_at
        }

        # Extract and directly append feedback fields
        for section in response.data:
            for field in section.get('fields', []):
                label = field.get('label', '')
                value = field.get('value', '')
                if label:  # Only add if label exists
                    response_data[label] = value
        
        final_data.append(response_data)
    
    return final_data
    
def report_sheet_generator():
    # Fetch all data once
    all_data = fetch_all_required_data()

    # Call functions to populate data for each sheet
    # Populate data for each reporting type
    lms_course_provider_data=populate_course_provider_sheet(all_data)
    lms_users_reporting_data = populate_lms_users_reporting_data(all_data)
    lms_batch_reporting_data = populate_lms_batch_reporting_data(all_data)
    afh_reporting_data = populate_AFH_reporting_data(all_data)
    course_provider_reporting_data = populate_course_provider_reporting_data(all_data)
    lms_time_spent_reporting_data = populate_lms_time_spent_reporting_data(all_data)
    lms_activity_logs_data = populate_lms_activity_logs_data(all_data)
    lms_live_class_logs_data = populate_lms_live_classes_logs_data(all_data)  # Assuming you have this function
    lms_assessment_logs_data = populate_lms_assessments_logs_data(all_data)  # Assuming you have this function
    lms_feedback_data=populate_lms_feedback_responses_data(all_data)

    # Initialize GDWrapper
    gd_wrapper = GDWrapper(speadsheet_id=settings.REPORT_SPEADSHEET_ID)

    # Update the Google Sheets with the populated data
    gd_wrapper.smart_update_sheet('LMS Course Providers', lms_course_provider_data,key_fields=['CourseProviderId','CourseProviderName'])
    gd_wrapper.update_sheet('LMS Users Reporting', lms_users_reporting_data)
    gd_wrapper.update_sheet('LMS Batch Reporting', lms_batch_reporting_data)
    gd_wrapper.update_sheet('AFH Reporting', afh_reporting_data)
    gd_wrapper.update_sheet('Course Provider Reporting', course_provider_reporting_data)
    gd_wrapper.update_sheet('LMS Time Spent Reporting', lms_time_spent_reporting_data)
    gd_wrapper.append_to_sheet('LMS Activity Logs', lms_activity_logs_data)
    gd_wrapper.append_to_sheet('LMS Live Class Logs', lms_live_class_logs_data)
    gd_wrapper.append_to_sheet('LMS Assessment Logs', lms_assessment_logs_data)
    gd_wrapper.update_sheet('LMS Feedback',lms_feedback_data)
    if settings.DEPLOYMENT_TYPE == "ECF":
        new_spreadsheet_name = (
            f"ORBIT/ECF LMS Reporting - {Utils.format_datetime(datetime.utcnow())}"
        )
        generate_sheet_without_test_users(all_data)
    else:
        new_spreadsheet_name = (
            f"LMS Reporting - {Utils.format_datetime(datetime.utcnow())}"
        )
    gd_wrapper.rename_spreadsheet(new_spreadsheet_name)



def generate_sheet_without_test_users(all_data):
    filtered_data={
        'students': all_data.get('filtered_students',[]),
        'user_profiles_map': all_data.get('filtered_user_profiles_map',{}),
        'course_map': all_data.get('course_map',{}),
        'batch_map': all_data.get('batch_map',{}),
        'user_course_batch_map': all_data.get('filtered_user_course_batch_map',{}),
        'activity_data': all_data.get('filtered_activity_data',[]),
        'meetings_data': all_data.get('filtered_meetings_data',[]),
        'assessments_data': all_data.get('filtered_assessments_data',[]),
        'course_providers_data': all_data.get('course_providers_data',[]),
        'feedback_responses': all_data.get('filtered_feedback_responses',[]),
        'reports_data':all_data.get('filtered_reports_data',[]),
    }    
    # Call functions to populate data for each sheet
    # Populate data for each reporting type
    lms_course_provider_data=populate_course_provider_sheet(filtered_data)
    lms_users_reporting_data = populate_lms_users_reporting_data(filtered_data)
    lms_batch_reporting_data = populate_lms_batch_reporting_data(filtered_data)
    afh_reporting_data = populate_AFH_reporting_data(filtered_data)
    course_provider_reporting_data = populate_course_provider_reporting_data(filtered_data)
    lms_time_spent_reporting_data = populate_lms_time_spent_reporting_data(filtered_data)
    lms_activity_logs_data = populate_lms_activity_logs_data(filtered_data)
    lms_live_class_logs_data = populate_lms_live_classes_logs_data(filtered_data)  # Assuming you have this function
    lms_assessment_logs_data = populate_lms_assessments_logs_data(filtered_data)  # Assuming you have this function
    lms_feedback_data=populate_lms_feedback_responses_data(filtered_data)

    # Initialize GDWrapper
    gd_wrapper = GDWrapper(speadsheet_id=settings.REPORT_SPEADSHEET_ID_WITHOUT_TEST_EMAILS)

    # Update the Google Sheets with the populated data
    gd_wrapper.smart_update_sheet('LMS Course Providers', lms_course_provider_data,key_fields=['CourseProviderId','CourseProviderName'])
    gd_wrapper.update_sheet('LMS Users Reporting', lms_users_reporting_data)
    gd_wrapper.update_sheet('LMS Batch Reporting', lms_batch_reporting_data)
    gd_wrapper.update_sheet('AFH Reporting', afh_reporting_data)
    gd_wrapper.update_sheet('Course Provider Reporting', course_provider_reporting_data)
    gd_wrapper.update_sheet('LMS Time Spent Reporting', lms_time_spent_reporting_data)
    gd_wrapper.append_to_sheet('LMS Activity Logs', lms_activity_logs_data)
    gd_wrapper.append_to_sheet('LMS Live Class Logs', lms_live_class_logs_data)
    gd_wrapper.append_to_sheet('LMS Assessment Logs', lms_assessment_logs_data)
    gd_wrapper.update_sheet('LMS Feedback',lms_feedback_data)
    if settings.DEPLOYMENT_TYPE == "ECF":
        new_spreadsheet_name = (
            f"ORBIT/ECF LMS Reporting (WITHOUT TEST USERS) - {Utils.format_datetime(datetime.utcnow())}"
        )
    else:
        new_spreadsheet_name = (
            f"LMS Reporting (WITHOUT TEST USERS) - {Utils.format_datetime(datetime.utcnow())}"
        )
    gd_wrapper.rename_spreadsheet(new_spreadsheet_name)