import datetime
import json
import logging
import os
import requests
import urllib.parse
from datetime import datetime, timedelta
from typing import List, Dict
import csv
from pathlib import Path

from dotenv import load_dotenv
from accounts.repositories import UserConfigMappingRepository
from accounts.models import UserConfigMapping
from course.repositories import BatchRepository, CourseRepository
from course.models import Batch
from custom_auth.services.custom_auth_service import CustomAuth
from custom_auth.repositories import UserProfileRepository
from custom_auth.services.sendgrid_service import SendgridService
from evaluation.management.register.utils import Utils
import firebase_admin
from accounts.usecases import RoleAssignmentUsecase
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

load_dotenv()

# Constants
BATCH_SIZE = 25
DELTA_DAYS = 7
CSC_TOKEN = "e2iOOEMOIOPEWNoiwr0932mlvhdzp8224lka9823u2nvnksrwoe2394204jfamnvzshiowu823nf9ccni239hn023ij2102n392h38hnc2nrf923c229pr23kau12u3"
CSC_URL = "https://csc.theearthcarefoundation.org/api/user_details"
ECF_URL = "https://theearthcarefoundation.org/userdetails.php"
ECF_API_KEY = "5432109876"

course_codes = settings.ORBIT_COURSE_CODES
logger = logging.getLogger(__name__)

# Add these constants after the existing constants
LOG_DIR = "logs"
LOG_FILE = "user_registration_log.csv"
HEADERS = ["Timestamp", "Email", "Password", "Status", "Error Message"]

class UserRegistrationData:
    def __init__(self, email: str, course_codes: str, user_data: dict):
        self.email = email
        self.course_codes = course_codes
        self.user_data = user_data

def get_csc_data(last_time: str, now_time: str) -> List[Dict]:
    """Fetch student registration data from CSC API"""
    try:
        url = f"{CSC_URL}?updated_from={last_time}&updated_to={now_time}"
        response = requests.post(url, headers={"Authorization": f"Bearer {CSC_TOKEN}"})
        response.raise_for_status()
        return response.json().get("data", [])
    except Exception as e:
        logger.error(f"Failed to fetch CSC data: {str(e)}")
        return []
    
def get_ecf_data(last_time: datetime, now_time: datetime) -> List[Dict]:
    """Fetch student registration data from ECF API"""
    try:
        url = f"{ECF_URL}?apikey={ECF_API_KEY}&updated_from={last_time}&updated_to={now_time}"
        print(url)
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch ECF data: {str(e)}")
        return []

def filter_and_update_data(data_list, course_codes):
    """Filters the data to include only relevant course codes"""
    return [
        {**data, "course_codes": ",".join(code for code in data["course_codes"].split(",") if code in course_codes)}
        for data in data_list
        if any(code in course_codes for code in data["course_codes"].split(","))
    ]

def create_user_and_assign_role(firebase_id, email, config: dict):
    """Creates a user in the database and assigns a role"""
    try:
        user = User.objects.get(firebase_uid=firebase_id)
    except User.DoesNotExist:
        user = User.objects.create(
            firebase_uid=firebase_id,
            email=email,
            is_active=True,
            username=firebase_id,
            first_name=config.get("fname", ""),
            last_name=config.get("lname", "")
        )
    UserProfileRepository.create_user_profile(user_id=user.id)
    RoleAssignmentUsecase.assign_role_from_config(user)

def format_dob(dob: str) -> str:
    """Formats date of birth to 'YYYY-MM-DD'"""
    for fmt in ("%d/%m/%Y", "%Y/%d/%m", "%Y-%d-%m", "%d-%m-%Y"):
        try:
            parsed_date = datetime.strptime(dob, fmt)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return dob  # Return original if no valid format found

def process_registration_data(csc_data: List[Dict],ecf_data: List[Dict]) -> Dict[str, UserRegistrationData]:
    """Processes registration data from CSC"""
    user_registrations = {}
    csc_data_list = filter_and_update_data(csc_data, course_codes)
    ecf_data_list = filter_and_update_data(ecf_data, course_codes)

    data_list = csc_data_list + ecf_data_list

    for entry in data_list:
        email = entry['email'].lower()
        entry_course_codes = entry['course_codes']

        if email in user_registrations:
            existing = user_registrations[email]
            combined_course_codes = set(existing.course_codes.split(","))
            combined_course_codes.update(entry_course_codes.split(","))
            existing.course_codes = ",".join(combined_course_codes)

            existing.user_data.update({
                'fname': entry['name'],
                'lname': entry['name'],
                'state': entry['statename'],
                'district': entry['district_name'],
                'phone': entry['phone'],
                'dob': format_dob(entry['dob'])
            })
        else:
            user_registrations[email] = UserRegistrationData(
                email=email,
                course_codes=entry_course_codes,
                user_data={
                    'fname': entry['name'],
                    'lname': entry['name'],
                    'state': entry['statename'],
                    'district': entry['district_name'],
                    'phone': entry['phone'],
                    'dob': format_dob(entry['dob'])
                }
            )

    return user_registrations

def setup_log_file():
    """Initialize log file if it doesn't exist"""
    try:
        # Get current directory path
        current_dir = Path(__file__).parent
        log_path = current_dir / LOG_FILE
        
        # Create file with headers if it doesn't exist
        if not log_path.exists():
            with open(log_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(HEADERS)
        
        return str(log_path)
    except Exception as e:
        logger.error(f"Failed to setup log file: {str(e)}")
        return None

def log_user_creation(email: str, password: str, status: str, error_msg: str = ""):
    """Log user creation details to CSV file"""
    try:
        log_path = setup_log_file()
        if log_path:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([timestamp, email, password, status, error_msg])
    except Exception as e:
        logger.error(f"Failed to log to CSV: {str(e)}")

def create_firebase_user(email: str, config: dict) -> tuple:
    """Creates a user in Firebase, assigns role in DB, and sends credentials"""
    password = Utils.generate_random_password()
    
    try:
        firebase_id = CustomAuth.create_user(email=email, password=password)
        create_user_and_assign_role(firebase_id, email, config)

        # Send credentials since this is a new user
        SendgridService.send_password_email(email, password)
        
        # Log successful user creation
        log_user_creation(email, password, "Success")
        return True, "User created in Firebase and credentials sent"
    
    except firebase_admin.auth.EmailAlreadyExistsError:
        # Log existing user
        log_user_creation(email, "", "Already Exists", "User already exists in Firebase")
        return True, "User already exists in Firebase"
    
    except ValueError as e:
        # Log invalid email error
        log_user_creation(email, "", "Failed", f"Invalid email format: {str(e)}")
        return False, "Invalid email format"

def update_user_config_mapping(registrations: Dict[str, UserRegistrationData]) -> List[Dict[str, str]]:
    """Updates UserConfigMapping and creates users in Firebase when needed"""
    summary = []

    for email, reg_data in registrations.items():
        mapping = UserConfigMappingRepository.get_user_config_mapping(email)

        if mapping is None:
            # New user: Create config mapping and Firebase user
            config = {
                "first_name": reg_data.user_data.get("fname", ""),
                "last_name": reg_data.user_data.get("lname", ""),
                "email_address": email,
                "role": "student",
                "course_codes": reg_data.course_codes,
                "user_data": [reg_data.user_data]
            }

            UserConfigMappingRepository.create_user_config_mapping(email=email, config=config)
            success, message = create_firebase_user(email, config)

            if success:
                summary.append({"email": email, "action": "Created new user and sent credentials."})
            else:
                logger.error(f"Failed to create Firebase user for {email}: {message}")
                summary.append({"email": email, "action": f"Failed to create Firebase user: {message}"})
        else:
            # Existing user: Update course codes if changed
            existing_course_codes = mapping.config.get('course_codes', [])
            if set(existing_course_codes) != set(reg_data.course_codes):
                mapping.config['course_codes'] = reg_data.course_codes
                mapping.save()
                summary.append({"email": email, "action": "Updated course codes."})
            else:
                summary.append({"email": email, "action": "No changes made."})

    return summary

def main():
    TIMESTAMP = datetime.now()
    now_time = TIMESTAMP.strftime("%Y-%m-%d")
    ecf_now_time = TIMESTAMP.strftime("%d-%m-%y")

    last_time = TIMESTAMP - timedelta(
        days=float(DELTA_DAYS)
    )
    # Initialize CustomLogger

    ecf_last_time = last_time.strftime("%d-%m-%y")
    last_time = last_time.strftime("%Y-%m-%d")

    # Fetch data from both APIs
    csc_data_list = get_csc_data(
            last_time=last_time, now_time=now_time
        )
    if "data" in csc_data_list:
        csc_data_list = list(csc_data_list["data"])


    ecf_data_list = get_ecf_data(
            last_time=ecf_last_time, now_time=ecf_now_time
        )
    


    ecf_data_list = []
    if "data" in ecf_data_list:
        ecf_data_list = list(ecf_data_list["data"])

    
    # Assuming processed_data is a dictionary returned from process_registration_data
    processed_data = process_registration_data(csc_data_list, ecf_data_list)
    # Update database and create users where needed
    summary = update_user_config_mapping(processed_data)
    print(summary)

if __name__ == "__main__":
    main()