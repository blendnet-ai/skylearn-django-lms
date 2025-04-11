import pandas as pd
from typing import Dict, List
from django.db import transaction
from accounts.models import UserConfigMapping
from custom_auth.services.custom_auth_service import CustomAuth
from custom_auth.services.sendgrid_service import SendgridService
from evaluation.management.register.utils import Utils
import logging
import json

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
                "Course ID",
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
        # Handle empty/NaN values with default values
        name = str(row["Name"]).strip() if pd.notna(row["Name"]) else ""
        name_parts = name.split(maxsplit=1)
        first_name = name_parts[0] if name_parts else ""
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        # Helper function to handle NaN values
        def clean_value(value, default=""):
            return str(value).strip() if pd.notna(value) else default

        return {
            "role": "student",
            "course_id": clean_value(row["Course ID"]),
            "batch_id": clean_value(row["Batch ID"]),
            "first_name": first_name,
            "last_name": last_name,
            "email_address": clean_value(row["Email"]).lower(),
            "phone": clean_value(row["Phone"]),
            "user_data": {
                "college_name": clean_value(row["College Name"]),
                "enrollment_status": clean_value(row["Enrollment Status"]),
                "centre_name": clean_value(row["Centre Name"]),
                "training_location_district": clean_value(
                    row["Training Location District Name"]
                ),
                "training_location_city": clean_value(
                    row["Training Location City Name"]
                ),
                "onboarding_source": clean_value(row["Onboarding Source"]),
                "state": clean_value(row["State"]),
                "district": clean_value(row["District"]),
            },
        }

    def _create_new_user(self, email: str, config: Dict) -> None:
        """Create new user with Firebase auth and config mapping"""
        password = Utils.generate_random_password()

        # Create Firebase user
        firebase_id = CustomAuth.create_user(email=email, password=password)

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

        # Update batch ID if provided
        if new_config.get("batch_id"):
            existing_batch_ids = set(existing_config.get("batch_id", "").split(","))
            existing_batch_ids.add(new_config["batch_id"])
            existing_config["batch_id"] = ",".join(filter(None, existing_batch_ids))

        # Update course ID if provided
        if new_config.get("course_id"):
            existing_course_ids = set(existing_config.get("course_id", "").split(","))
            existing_course_ids.add(new_config["course_id"])
            existing_config["course_id"] = ",".join(filter(None, existing_course_ids))

        # Update other fields
        fields_to_update = ["phone", "first_name", "last_name", "role"]
        for field in fields_to_update:
            if new_config.get(field):
                existing_config[field] = new_config[field]

        # Ensure proper JSON serialization before saving
        mapping.config = json.loads(json.dumps(existing_config))
        mapping.save()
