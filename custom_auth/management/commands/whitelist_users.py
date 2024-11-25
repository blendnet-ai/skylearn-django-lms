from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from InstituteConfiguration.repositories import InstituteRepository
from custom_auth.repositories import UserProfileRepository
from custom_auth.services.custom_auth_service import CustomAuth
from data_repo.repositories import ConfigMapRepository
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper
from evaluation.management.register.utils import Utils

import firebase_admin


User = get_user_model()


def whitelist_users():
    whitelisting_config = ConfigMapRepository.get_config_by_tag(
        tag="whitelisting_config"
    )

    whitelisting_speadsheet_id = whitelisting_config["speadsheet_id"]

    gd_wrapper = GDWrapper(whitelisting_speadsheet_id)

    errors = []

    try:
        sheet_users = gd_wrapper.get_sheet_as_json("data")

        for sheet_user in sheet_users:
            try:
                if sheet_user["status"] == "Done":
                    continue

                email = sheet_user["email"]
                password = Utils.generate_random_password()
                firebase_id = None

                try:
                    firebase_id = CustomAuth.create_user(email=email, password=password)
                except firebase_admin.auth.EmailAlreadyExistsError:
                    firebase_id = CustomAuth.get_user_by_email(email)
                    if sheet_user["password"] == "":
                        password = "User already in firebase, can't get the password"

                sheet_user["password"] = password

                db_user, _ = User.objects.get_or_create(
                    username=firebase_id, defaults={"email": email}
                )
                user_id = db_user.id

                UserProfileRepository.create_user_profile(user_id=user_id)

                UserProfileRepository.set_name(user_id, sheet_user["name"])
                UserProfileRepository.set_onboarding_complete(user_id)

                institute_name = sheet_user["institute"]

                if institute_name == "":
                    UserProfileRepository.set_institute(user_id=user_id, institute=None)
                else:
                    institute = InstituteRepository.get_institute_by_name(
                        institute_name
                    )
                    if not institute:
                        raise ValueError(f"Institute not found - {institute_name}.")
                    UserProfileRepository.set_institute(
                        user_id=user_id, institute=institute
                    )

                sheet_user["status"] = "Done"
            except Exception as e:
                error = {"email": email, "error": f"{e}"}
                errors.append(error)
                sheet_user["status"] = "Error"

    except Exception as e:
        error = {"email": "Script", "error": f"{e}"}
        errors.append(error)

    if len(errors) <= 0:
        error = {"email": "", "error": f""}
        errors.append(error)

    gd_wrapper.update_sheet("errors", errors)
    gd_wrapper.update_sheet("data", sheet_users)


class Command(BaseCommand):
    help = "Command to whitelist users present the whitelisting spreadsheet"

    def handle(self, *args, **options):
        whitelist_users()
