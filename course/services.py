import pandas as pd
from typing import Dict, List
from django.db import transaction
from accounts.models import UserConfigMapping
from custom_auth.services.custom_auth_service import CustomAuth
from custom_auth.services.sendgrid_service import SendgridService
from evaluation.management.register.utils import Utils
from course.models import Course, Batch
from django.core.exceptions import ValidationError
import logging
import json
import re
import firebase_admin
import csv
from pathlib import Path

logger = logging.getLogger(__name__)


class BulkEnrollmentService:
    def __init__(self, file):
        self.file = file
        self.results = {"success": [], "failed": []}

    def process(self) -> Dict:
        """Process the uploaded file and create/update user configs"""
        try:
            df = pd.read_excel(self.file)
            required_columns = [
                "Name",
                "Email",
                "College Name",
                "Enrollment Status",
                "Centre Name",
                "Training Location District Name",
                "Training Location City Name",
                "Course Code",
                "Batch ID",
                "Onboarding Source",
                "State",
                "District",
                "Phone",
            ]

            # Validate columns
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(
                    f"Missing required columns: {', '.join(missing_columns)}"
                )

            # Process each row
            for _, row in df.iterrows():
                self._process_row(row)

            return {
                "success_count": len(self.results["success"]),
                "failed_count": len(self.results["failed"]),
                "success": self.results["success"],
                "failed": self.results["failed"],
            }

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            raise

    # Helper function to handle NaN values
    @staticmethod
    def clean_value(value, default=""):
        """Helper function to handle NaN values with special handling for batch_id"""
        if pd.isna(value):
            return default
        # Handle batch_id as integer
        if isinstance(value, (int, float)) and str(value).replace(".", "").isdigit():
            return int(float(value))  # Convert float to int (e.g., 1.0 -> 1)
        return str(value).strip()

    @transaction.atomic
    def _process_row(self, row: pd.Series) -> None:
        """Process a single row from the file"""
        try:
            email = row["Email"].lower().strip()
            if not email or pd.isna(email):
                raise ValueError("Missing email")

            # Create config
            config = self._create_config(row)

            # Check if user exists in UserConfigMapping
            user_mapping = UserConfigMapping.objects.filter(email=email).first()

            try:
                # Try to get Firebase user
                firebase_user = CustomAuth.get_user_by_email(email)
                firebase_exists = True
            except firebase_admin.auth.UserNotFoundError:
                firebase_exists = False

            if user_mapping and firebase_exists:
                # User exists in both Firebase and UserConfigMapping - update config
                self._update_existing_mapping(user_mapping, config)
                message = "Updated existing user config"
            elif user_mapping and not firebase_exists:
                # User exists in UserConfigMapping but not in Firebase - create Firebase user
                password = Utils.generate_random_password()
                firebase_id = CustomAuth.create_user(email=email, password=password)
                SendgridService.send_password_email(email, password)
                self._update_existing_mapping(user_mapping, config)
                message = "Created Firebase user and updated config"
            elif not user_mapping and firebase_exists:
                # User exists in Firebase but not in UserConfigMapping - create mapping
                UserConfigMapping.objects.create(email=email, config=config)
                message = "Created user config for existing Firebase user"
            else:
                # New user - create both Firebase user and UserConfigMapping
                self._create_new_user(email, config)
                message = "Created new user with Firebase auth and config"

            self.results["success"].append({"email": email, "message": message})

        except Exception as e:
            logger.error(
                f"Error processing row for email {row.get('Email', 'No Email')}: {str(e)}"
            )
            self.results["failed"].append(
                {"email": row.get("Email", "No Email Found"), "error": str(e)}
            )

    def _create_config(self, row: pd.Series) -> Dict:
        """Create config dictionary from row data"""
        # Email validation
        email = BulkEnrollmentService.clean_value(row["Email"]).lower()
        if not email:
            raise ValidationError("Email address is required")

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValidationError(f"Invalid email format: {email}")

        # Phone validation
        phone = BulkEnrollmentService.clean_value(row["Phone"])
        if phone:
            # Remove any non-digit characters
            phone = re.sub(r"\D", "", phone)
            # Check if phone number is valid (10 digits)
            if not re.match(r"^\d{10}$", phone):
                raise ValidationError(
                    f"Invalid phone number format: {row['Phone']}. Must be 10 digits."
                )

        # Validate course and batch IDs
        course_id = BulkEnrollmentService.clean_value(row["Course Code"])
        batch_id = BulkEnrollmentService.clean_value(row["Batch ID"])

        # Check if course_id is provided
        if not course_id:
            raise ValidationError("Course Code is required")

        # Check if batch_id is provided
        if not batch_id:
            raise ValidationError("Batch ID is required")

        # Validate Course Code
        if course_id:
            course = Course.objects.filter(code=course_id).first()
            if not course:
                raise ValidationError(f"Invalid Course Code: {course_id}")

        # Validate batch ID
        if batch_id:
            if not isinstance(batch_id, int):
                raise ValidationError(f"Batch ID must be an integer, got: {batch_id}")
            batch = Batch.objects.filter(id=batch_id).first()
            if not batch:
                raise ValidationError(f"Invalid batch ID: {batch_id}")
            # Verify batch belongs to course
            if str(batch.course.code) != str(course_id):
                raise ValidationError(
                    f"Batch {batch_id} does not belong to course {course_id}"
                )

        name = str(row["Name"]).strip() if pd.notna(row["Name"]) else ""
        name_parts = name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        return {
            "role": "student",
            "course_id": course_id,
            "batch_id": batch_id,
            "first_name": first_name,
            "last_name": last_name,
            "email_address": email,
            "phone": phone,
            "user_data": {
                "college_name": BulkEnrollmentService.clean_value(row["College Name"]),
                "enrollment_status": BulkEnrollmentService.clean_value(
                    row["Enrollment Status"]
                ),
                "centre_name": BulkEnrollmentService.clean_value(row["Centre Name"]),
                "training_location_district": BulkEnrollmentService.clean_value(
                    row["Training Location District Name"]
                ),
                "training_location_city": BulkEnrollmentService.clean_value(
                    row["Training Location City Name"]
                ),
                "onboarding_source": BulkEnrollmentService.clean_value(
                    row["Onboarding Source"]
                ),
                "state": BulkEnrollmentService.clean_value(row["State"]),
                "district": BulkEnrollmentService.clean_value(row["District"]),
            },
        }

    def _create_new_user(self, email: str, config: Dict) -> None:
        """Create new user with Firebase auth and config mapping"""
        password = Utils.generate_random_password()

        # Create Firebase user
        firebase_id = CustomAuth.create_user(email=email, password=password)
        csv_path = Path("user_creds.csv")
        file_exists = csv_path.exists()

        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["email", "password", "created_at"])
            if not file_exists:
                writer.writeheader()
            writer.writerow(
                {
                    "email": email,
                    "password": password,
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
        # Create config mapping - ensure config is JSON serializable
        UserConfigMapping.objects.create(
            email=email,
            config=json.loads(json.dumps(config)),  # Ensure proper JSON serialization
        )

        # Send credentials email
        SendgridService.send_password_email(email, password)

    def _update_existing_mapping(
        self, mapping: UserConfigMapping, new_config: Dict
    ) -> None:
        """Update existing user mapping with new data"""
        existing_config = mapping.config

        # Update user data
        if "user_data" in existing_config:
            existing_config["user_data"].update(new_config["user_data"])
        else:
            existing_config["user_data"] = new_config["user_data"]

        # Update batch ID if provided - convert all values to strings
        # Update batch ID if provided - handle both string and integer cases
        if new_config.get("batch_id"):
            existing_batch_id = existing_config.get("batch_id", "")
            # Convert to string and handle both integer and string cases
            existing_batch_ids = set()
            if existing_batch_id:
                if isinstance(existing_batch_id, (int, float)):
                    existing_batch_ids.add(str(int(existing_batch_id)))
                else:
                    existing_batch_ids.update(
                        bid for bid in str(existing_batch_id).split(",") if bid
                    )
            existing_batch_ids.add(str(new_config["batch_id"]))
            existing_config["batch_id"] = ",".join(existing_batch_ids)

        # Update Course Code if provided - handle both string and integer cases
        if new_config.get("course_id"):
            existing_course_id = existing_config.get("course_id", "")
            existing_course_ids = set()
            if existing_course_id:
                if isinstance(existing_course_id, (int, float)):
                    existing_course_ids.add(str(existing_course_id))
                else:
                    existing_course_ids.update(
                        cid for cid in str(existing_course_id).split(",") if cid
                    )
            existing_course_ids.add(str(new_config["course_id"]))
            existing_config["course_id"] = ",".join(existing_course_ids)

        # Update other fields
        fields_to_update = ["phone", "first_name", "last_name", "role"]
        for field in fields_to_update:
            if new_config.get(field):
                existing_config[field] = new_config[field]

        # Ensure proper JSON serialization before saving
        mapping.config = json.loads(json.dumps(existing_config))
        mapping.save()


from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from evaluation.models import Question, AssessmentGenerationConfig
from django.db.models import Q
from dataclasses import dataclass


@dataclass
class QuestionTypeResult:
    available_count: int
    requested_count: int
    question_ids: List[int]

    @property
    def has_enough_questions(self):
        return self.available_count >= self.requested_count


class AssessmentConfigGenerator:
    QUESTION_TYPE_MAPPING = {
        "objective": {
            "answer_type": Question.AnswerType.MCQ,
            "category": Question.Category.LANGUAGE,
        },
        "listening": {
            "answer_type": Question.AnswerType.MMCQ,
            "sub_category": Question.SubCategory.LISTENING,
        },
        "speaking": {
            "answer_type": Question.AnswerType.VOICE,
            "sub_category": Question.SubCategory.SPEAKING,
        },
        "reading": {
            "answer_type": Question.AnswerType.MMCQ,
            "sub_category": Question.SubCategory.RC,
        },
        "writing": {
            "answer_type": Question.AnswerType.SUBJECTIVE,
            "sub_category": Question.SubCategory.WRITING,
        },
    }

    @staticmethod
    def get_questions_by_type(question_type: str, count: int) -> QuestionTypeResult:
        """
        Get specified number of question IDs for given type and return availability info
        """
        mapping = AssessmentConfigGenerator.QUESTION_TYPE_MAPPING[question_type]
        query = Q(answer_type=mapping["answer_type"])

        if question_type == "objective":
            query &= Q(category=mapping["category"])
        elif mapping.get("sub_category"):
            query &= Q(sub_category=mapping["sub_category"])

        questions = list(Question.objects.filter(query).values_list("id", flat=True))
        available_count = len(questions)
        actual_count = min(available_count, count)

        return QuestionTypeResult(
            available_count=available_count,
            requested_count=count,
            question_ids=questions[:actual_count],
        )

    @staticmethod
    def generate_config(
        question_counts: Dict[str, int],
        name: str,
        module_id: int,
        start_date: datetime,
        end_date: datetime,
        due_date: datetime = None,
        duration: int = 60,
        assessment_generator_class_name="QuestionPoolBasedAssessment",
        evaluator_class_name="Question Based",
    ) -> Tuple[AssessmentGenerationConfig, Dict]:
        """
        Generate assessment config with sections based on question types and counts

        Returns:
            Tuple containing:
            - The created AssessmentGenerationConfig
            - Dict with info about question availability
        """
        subcategories = []
        total_questions = 0
        question_availability = {}

        for qtype, count in question_counts.items():
            if count > 0:
                result = AssessmentConfigGenerator.get_questions_by_type(qtype, count)
                question_availability[qtype] = {
                    "requested": result.requested_count,
                    "available": result.available_count,
                    "sufficient": result.has_enough_questions,
                }

                if result.question_ids:
                    subcategories.append(
                        {
                            "number": len(result.question_ids),
                            "skippable": True,
                            "section_name": qtype.capitalize(),
                            "question_pool": result.question_ids,
                        }
                    )
                    total_questions += len(result.question_ids)

        unique_name = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        config = AssessmentGenerationConfig.objects.create(
            assessment_name=unique_name,
            assessment_display_name=name,
            start_date=start_date,
            end_date=end_date,
            due_date=due_date,
            test_duration=timedelta(minutes=duration),
            kwargs={
                "category": Question.Category.LANGUAGE,
                "total_number": total_questions,
                "subcategories": subcategories,
            },
            enabled=True,
            assessment_generation_class_name=assessment_generator_class_name,
            evaluator_class_name=evaluator_class_name,
        )

        return config, question_availability


from typing import Dict, List, Tuple
from datetime import timedelta
import pandas as pd
import logging
from django.core.exceptions import ValidationError
from evaluation.models import Question
from storage_service.azure_storage import AzureStorageService
import os
import requests
import tempfile
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class QuestionUploadResult:
    def __init__(self):
        self.successful: List[Dict] = []  # {title: str, id: int}
        self.failed: List[Dict] = []  # {title: str, reason: str}


class QuestionUploader:
    UPLOADER_CONFIGS = {
        "objective": {
            "required_columns": [
                "Question",
                "Option 1",
                "Option 2",
                "Option 3",
                "Correct Option",
            ],
            "answer_type": Question.AnswerType.MCQ,
            "category": Question.Category.LANGUAGE,
            "sub_category": Question.SubCategory.QUANT,
        },
        "reading": {
            "required_columns": [
                "Task Number",
                "Instructions",
                "Passage",
                "Question",
                "Option 1",
                "Option 2",
                "Option 3",
                "Option 4",
                "Correct Option",
            ],
            "answer_type": Question.AnswerType.MMCQ,
            "sub_category": Question.SubCategory.RC,
        },
        "writing": {
            "required_columns": ["Question"],
            "answer_type": Question.AnswerType.SUBJECTIVE,
            "sub_category": Question.SubCategory.WRITING,
        },
        "speaking": {
            "required_columns": ["Question"],
            "answer_type": Question.AnswerType.VOICE,
            "sub_category": Question.SubCategory.SPEAKING,
        },
        "listening": {
            "required_columns": [
                "Question",
                "Audio Link",
                "Option 1",
                "Option 2",
                "Correct Option",
            ],
            "answer_type": Question.AnswerType.MMCQ,
            "sub_category": Question.SubCategory.LISTENING,
        },
    }

    def __init__(self):
        self.default_time = timedelta(minutes=1)
        self.storage_service = AzureStorageService()
        self.container_name = "listening-audios"

    def validate_columns(self, df: pd.DataFrame, question_type: str) -> None:
        required_cols = self.UPLOADER_CONFIGS[question_type]["required_columns"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValidationError(
                f"Missing required columns for {question_type}: {', '.join(missing_cols)}"
            )

    def get_file_id_from_url(self, url: str) -> str:
        """Extract file ID from Google Drive URL"""
        parsed_url = urlparse(url)
        if "drive.google.com" in parsed_url.netloc:
            if "file/d/" in url:
                file_id = url.split("file/d/")[1].split("/")[0]
            else:
                file_id = parsed_url.query.split("id=")[1].split("&")[0]
            return file_id
        return None

    def download_from_drive(self, drive_url: str) -> str:
        """Download file from Google Drive"""
        try:
            file_id = self.get_file_id_from_url(drive_url)
            if not file_id:
                raise ValueError(f"Invalid Google Drive URL: {drive_url}")

            download_url = f"https://drive.google.com/uc?id={file_id}"

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                response = requests.get(download_url)
                response.raise_for_status()
                temp_file.write(response.content)
                temp_path = temp_file.name

            return temp_path

        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            raise

    def upload_audio_to_azure(self, gdrive_url: str, blob_name: str) -> str:
        """Downloads audio from Google Drive and uploads to Azure"""
        try:
            temp_audio_path = self.download_from_drive(gdrive_url)

            with open(temp_audio_path, "rb") as file:
                content = file.read()
                azure_url = self.storage_service.upload_blob(
                    container_name=self.container_name,
                    blob_name=blob_name,
                    content=content,
                    content_type="audio/mpeg",
                    overwrite=True,
                )

            # Clean up temporary file
            os.unlink(temp_audio_path)

            return azure_url

        except Exception as e:
            logger.error(f"Error uploading audio {gdrive_url}: {str(e)}")
            raise

    def process_objective_question(self, row: pd.Series) -> Dict:
        return {
            "question": row["Question"],
            "options": [row[f"Option {i}"] for i in range(1, 4)],
            "answer": int(row["Correct Option"]) - 1,
        }

    def process_reading_question(self, group: pd.DataFrame) -> Dict:
        sub_questions = []
        for _, row in group.iterrows():
            options = [
                row[f"Option {i}"] for i in range(1, 5) if pd.notna(row[f"Option {i}"])
            ]
            sub_questions.append(
                {
                    "question": row["Question"],
                    "options": options,
                    "answer": int(row["Correct Option"]) - 1,
                }
            )
        return {
            "paragraph": f"{group['Instructions'].iloc[0]}\n{group['Passage'].iloc[0]}",
            "task_number": int(group["Task Number"].iloc[0]),
            "questions": sub_questions,
        }

    def process_writing_question(self, row: pd.Series) -> Dict:
        """Process writing questions with default medium level"""
        return {"question": row["Question"], "level": "easy"}

    def process_listening_question(self, group: pd.DataFrame) -> Dict:
        """Process grouped listening questions with shared audio"""
        try:
            # Get audio URL from first row since it's same for group
            audio_url = group["Audio Link"].iloc[0]

            # Upload audio to Azure
            file_id = self.get_file_id_from_url(audio_url)
            audio_blob_name = f"{file_id}.mp3"
            azure_audio_url = self.upload_audio_to_azure(audio_url, audio_blob_name)

            # Process all questions for this audio
            sub_questions = []
            for _, row in group.iterrows():
                sub_question = {
                    "question": row["Question"],
                    "options": [row["Option 1"], row["Option 2"]],
                    "answer": int(row["Correct Option"]) - 1,
                }
                sub_questions.append(sub_question)

            # Return complete question data
            return {"questions": sub_questions, "audio_url": azure_audio_url}

        except Exception as e:
            logger.error(f"Error processing listening questions for audio: {audio_url}")
            logger.error(str(e))
            raise ValidationError(f"Error processing listening questions: {str(e)}")

    def process_speaking_question(self, row: pd.Series) -> Dict:
        """Process speaking questions with empty hint"""
        return {
            "question": row["Question"],
            "hint": "",  # Empty hint field for speaking questions
        }

    def get_question_signature(self, question_data: Dict, question_type: str) -> str:
        """Generate a unique signature for a question based on its content"""
        if question_type == "reading":
            signature = f"{question_data['paragraph']}"
        elif question_type == "listening":
            signature = f"{question_data.get('audio_url', '')}"
        else:
            signature = question_data["question"]
        return signature.strip().lower()

    def is_question_duplicate(
        self, question_data: Dict, question_type: str, config: Dict
    ) -> bool:
        """Check if question already exists"""
        signature = self.get_question_signature(question_data, question_type)
        query = Q(
            answer_type=config["answer_type"], sub_category=config["sub_category"]
        )
        existing_questions = Question.objects.filter(query)

        return any(
            self.get_question_signature(q.question_data, question_type) == signature
            for q in existing_questions
        )

    def upload_questions(self, file, question_type: str) -> QuestionUploadResult:
        """Upload questions from CSV file based on question type"""
        result = QuestionUploadResult()
        config = self.UPLOADER_CONFIGS[question_type]

        try:
            df = (
                pd.read_excel(file)
                if file.name.endswith(".xlsx")
                else pd.read_csv(file)
            )
            self.validate_columns(df, question_type)
            questions_to_create = []

            if question_type == "reading":
                for _, group in df.groupby("Task Number"):
                    try:
                        question_data = self.process_reading_question(group)
                        if self.is_question_duplicate(
                            question_data, question_type, config
                        ):
                            result.successful.append(
                                {
                                    "title": f"Reading Task {group['Task Number'].iloc[0]}",
                                    "status": "duplicate",
                                }
                            )
                        else:
                            questions_to_create.append(
                                self.create_question_object(question_data, config)
                            )
                            result.successful.append(
                                {
                                    "title": f"Reading Task {group['Task Number'].iloc[0]}",
                                    "status": "created",
                                }
                            )
                    except Exception as e:
                        result.failed.append(
                            {
                                "title": f"Reading Task {group['Task Number'].iloc[0]}",
                                "reason": str(e),
                            }
                        )

            elif question_type == "listening":
                for audio_url, group in df.groupby("Audio Link"):
                    try:
                        question_data = self.process_listening_question(group)
                        if self.is_question_duplicate(
                            question_data, question_type, config
                        ):
                            result.successful.append(
                                {
                                    "title": f"Listening Audio {audio_url}",
                                    "question_count": len(group),
                                    "status": "duplicate",
                                }
                            )
                        else:
                            questions_to_create.append(
                                self.create_question_object(question_data, config)
                            )
                            result.successful.append(
                                {
                                    "title": f"Listening Audio {audio_url}",
                                    "question_count": len(group),
                                    "status": "created",
                                }
                            )
                    except Exception as e:
                        result.failed.append(
                            {"title": f"Listening Audio {audio_url}", "reason": str(e)}
                        )

            else:
                for idx, row in df.iterrows():
                    try:
                        processor = getattr(self, f"process_{question_type}_question")
                        question_data = processor(row)
                        if self.is_question_duplicate(
                            question_data, question_type, config
                        ):
                            result.successful.append(
                                {
                                    "title": row["Question"],
                                    "status": "duplicate",
                                }
                            )
                        else:
                            questions_to_create.append(
                                self.create_question_object(question_data, config)
                            )
                            result.successful.append(
                                {
                                    "title": row["Question"],
                                    "status": "created",
                                }
                            )
                    except Exception as e:
                        result.failed.append(
                            {"title": row["Question"], "reason": str(e)}
                        )

            # Bulk create questions and update IDs for only non-duplicate entries
            if questions_to_create:
                created_questions = Question.objects.bulk_create(questions_to_create)
                created_idx = 0
                for i in range(len(result.successful)):
                    if result.successful[i]["status"] == "created":
                        # result.successful[i]["id"] = created_questions[created_idx].id
                        created_idx += 1

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            raise ValidationError(f"Error processing file: {str(e)}")

        return result

    def create_question_object(self, question_data: Dict, config: Dict) -> Question:
        return Question(
            answer_type=config["answer_type"],
            question_data=question_data,
            category=config.get("category", Question.Category.LANGUAGE),
            sub_category=config["sub_category"],
            audio_url=question_data.get("audio_url", None),
            time_required=self.default_time,
            tags=[],
        )
