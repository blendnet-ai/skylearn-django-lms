from datetime import datetime
from django.contrib.auth import get_user_model
from course.repositories import CourseRepository, BatchRepository
from accounts.repositories import StudentRepository
from custom_auth.repositories import UserProfileRepository
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper
from evaluation.management.generate_status_sheet.utils import Utils
from reports.repositories import UserCourseReportRepository
from accounts.usecases import StudentProfileUsecase

User = get_user_model()

# Optimized function to get all required data at once
def fetch_all_required_data():
    # Fetch all students
    students = StudentRepository.get_all_students()

    # Fetch user IDs for profiles
    user_ids = [student.student.id for student in students]

    # Fetch all user profiles in one query
    user_profiles = UserProfileRepository.get_all_profiles_for_user_ids(user_ids)

    # Map user_id to profile for quick lookup
    user_profiles_map = {profile.user_id_id: profile for profile in user_profiles}

    # Fetch all courses and batches
    courses = CourseRepository.get_all_courses()
    batches = BatchRepository.get_all_batches()

    # Create a map of course details by course_id for quick lookup
    course_map = {course.get('id'): course for course in courses}

    # Create a map of batch details by batch_id for quick lookup
    batch_map = {batch.id: batch for batch in batches}

    # Create a map of user_id to course_name and batch_id for each student
    user_course_batch_map = {}
    for student in students:
        batches = list(student.batches.all())  # Fetch all related batches
        batch_id = batches[0].id if batches else None
        course_name = batch_map.get(batch_id).course.title if batch_id else None
        user_course_batch_map[student.student.id] = {
            "course_name": course_name,
            "batch_id": batch_id
        }

    # Return all the data as a dictionary for easy passing
    return {
        'students': students,
        'user_profiles_map': user_profiles_map,
        'course_map': course_map,
        'batch_map': batch_map,
        'user_course_batch_map': user_course_batch_map
    }

# Function for Sheet 1 - Populate user data
def populate_sheet_1(data):
    student_data = []
    for user_id, user_profile in data['user_profiles_map'].items():
        user = user_profile.user_id  # Get the user object for this user_profile
        student_data.append({
            "StudentID": user.id,
            "First Name": user.first_name,  # From User model
            "Last Name": user.last_name,  # From User model
            "Full Name": UserProfileRepository.fetch_value_from_form('name', user_profile.user_data),
            "DOB": UserProfileRepository.fetch_value_from_form('dob', user_profile.user_data),
            "Gender": UserProfileRepository.fetch_value_from_form('gender', user_profile.user_data),
            "Email": user.email,  # From User model
            "Phone": user_profile.phone,  # From UserProfile
            "College": UserProfileRepository.fetch_value_from_form('college', user_profile.user_data),
            "State": UserProfileRepository.fetch_value_from_form('state', user_profile.user_data),
            "District": UserProfileRepository.fetch_value_from_form('district', user_profile.user_data),
        })
    return student_data

# Function for Sheet 2 - Populate course data
def populate_sheet_2(data):
    course_data = []
    for course_id, course in data['course_map'].items():
        course_data.append({
            "name": course.get('title'),
            "id": course.get('id'),
            "duration": course.get('duration'),
            "code": course.get('code')
        })
    return course_data

# Function for Sheet 3 - Populate batch data
def populate_sheet_3(data):
    batch_data = []
    for batch_id, batch in data['batch_map'].items():
        batch_data.append({
            "batch id": batch.id,
            "course_id": batch.course_id,
            "start date": batch.created_at
        })
    return batch_data

# Function for Sheet 4 - Populate student batch association
def populate_sheet_4(data):
    student_batch_data = []
    for student in data['students']:
        batches = list(student.batches.all())  # Fetch all related batches
        batch_id = batches[0].id if batches else None
        student_batch_data.append({
            "student id": student.student.id,
            "batch id": batch_id,
            "enrollment date": student.student.date_joined,
            "section": None
        })
    return student_batch_data

# Function for Sheet 5 - Populate user profile and additional data
def populate_sheet_5(data):
    profile_data = []
    for user_id, user_profile in data['user_profiles_map'].items():
        user = user_profile.user_id  # Get the user object for this user_profile
        profile_data.append({
            "Beneficiary ID (Full Adhaar Number)": UserProfileRepository.fetch_value_from_form('aadharNumber', user_profile.user_data),
            "Enrollment Date (DD/MM/YY)": user.date_joined,
            "Name": user.get_full_name,
            "Age": StudentProfileUsecase._calculate_age(user_profile.user_data),
            "Gender": UserProfileRepository.fetch_value_from_form('gender', user_profile.user_data),
            "Phone": user_profile.phone,
            "State": UserProfileRepository.fetch_value_from_form('state', user_profile.user_data),
            "District": UserProfileRepository.fetch_value_from_form('district', user_profile.user_data),
            "Highest Qualification": UserProfileRepository.fetch_value_from_form('highestQualification', user_profile.user_data),
            "Annual Income in INR": UserProfileRepository.fetch_value_from_form('annualIncome', user_profile.user_data),
            "DOB": UserProfileRepository.fetch_value_from_form('dob', user_profile.user_data),
            "Email ID": user.email,  # From User model
            "Parent/Guardian Name": UserProfileRepository.fetch_value_from_form('parentGuardianName', user_profile.user_data),
            "Parent/Guardian Phone Number": UserProfileRepository.fetch_value_from_form('parentGuardianPhone', user_profile.user_data),
            "Parent / Guardian Occupation": UserProfileRepository.fetch_value_from_form('parentGuardianOccupation', user_profile.user_data),
            "Beneficiary Work Experience (in Years)": UserProfileRepository.fetch_value_from_form('workExperience', user_profile.user_data),
            "Enrollment Status": "Enrolled"
        })
    return profile_data

# Function for Sheet 6 - Populate reports data
def populate_sheet_6(data):
    final_data = []
    reports_data = UserCourseReportRepository.get_reports_data()

    for report in reports_data:
        user_profile = data['user_profiles_map'].get(report.user_id)
        course_info = data['user_course_batch_map'].get(report.user_id)
        user = report.user  # User object is accessible directly from the report
        final_data.append({
            'id': report.id,
            'first name': user.first_name,  # From User model
            'last name': user.last_name,  # From User model
            'gender': UserProfileRepository.fetch_value_from_form('gender', user_profile.user_data),
            'dob': UserProfileRepository.fetch_value_from_form('dob', user_profile.user_data),
            'email': user.email,  # From User model
            'state': UserProfileRepository.fetch_value_from_form('state', user_profile.user_data),
            'district': UserProfileRepository.fetch_value_from_form('district', user_profile.user_data),
            'department': UserProfileRepository.fetch_value_from_form('department', user_profile.user_data),
            'project': UserProfileRepository.fetch_value_from_form('project', user_profile.user_data),
            'phone': user_profile.phone,  # From UserProfile
            'course_name': course_info.get("course_name"),
            'batch id': course_info.get("batch_id"),
            'total time spent on videos': report.resource_time_video,
            'total time spent on reading': report.resource_time_reading,
            'total time spent in live classes': report.time_spent_in_live_classes,
            'total_learning_time': report.total_time_spent,
            'number of classes attended': report.classes_attended,
            'number of classes missed': report.total_classes - report.classes_attended,
            'attendance_percentage': (report.classes_attended / (report.classes_attended + (report.total_classes - report.classes_attended))) * 100 if report.total_classes else 0
        })
    return final_data

# Fetch all data once
all_data = fetch_all_required_data()

# Call functions to populate data for each sheet
BN_Users_data = populate_sheet_1(all_data)
BN_Courses_data = populate_sheet_2(all_data)
BN_Batches_data = populate_sheet_3(all_data)
BN_Enrollments_data = populate_sheet_4(all_data)
AFH_data = populate_sheet_5(all_data)
Orbit_data = populate_sheet_6(all_data)

gd_wrapper = GDWrapper('1Xr6k01UA_LLZoOhVDoaVu276pCL7pw0xwBdFStzREOM')
gd_wrapper.update_sheet('BN_Users',BN_Users_data)
gd_wrapper.update_sheet('BN_Courses',BN_Courses_data)
gd_wrapper.update_sheet('BN_Batches',BN_Batches_data)
gd_wrapper.update_sheet('BN_Enrollments',BN_Enrollments_data)
gd_wrapper.update_sheet('AFH',AFH_data)
gd_wrapper.update_sheet('Orbit',Orbit_data)

new_spreadsheet_name = (
    f"LMS Reporting - {Utils.format_datetime(datetime.utcnow())}"
)
gd_wrapper.rename_spreadsheet(new_spreadsheet_name)

# You can now proceed to update the sheets with the corresponding data


def report_sheet_generator():
    # Fetch all data once
    all_data = fetch_all_required_data()

    # Call functions to populate data for each sheet
    BN_Users_data = populate_sheet_1(all_data)
    BN_Courses_data = populate_sheet_2(all_data)
    BN_Batches_data = populate_sheet_3(all_data)
    BN_Enrollments_data = populate_sheet_4(all_data)
    AFH_data = populate_sheet_5(all_data)
    Orbit_data = populate_sheet_6(all_data)

    gd_wrapper = GDWrapper('1Xr6k01UA_LLZoOhVDoaVu276pCL7pw0xwBdFStzREOM')
    gd_wrapper.update_sheet('BN_Users',BN_Users_data)
    gd_wrapper.update_sheet('BN_Courses',BN_Courses_data)
    gd_wrapper.update_sheet('BN_Batches',BN_Batches_data)
    gd_wrapper.update_sheet('BN_Enrollments',BN_Enrollments_data)
    gd_wrapper.update_sheet('AFH',AFH_data)
    gd_wrapper.update_sheet('Orbit',Orbit_data)

    new_spreadsheet_name = (
        f"LMS Reporting - {Utils.format_datetime(datetime.utcnow())}"
    )
    gd_wrapper.rename_spreadsheet(new_spreadsheet_name)


