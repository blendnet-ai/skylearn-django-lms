from custom_auth.repositories import UserProfileRepository
from custom_auth.services.custom_auth_service import CustomAuth
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper

from InstituteConfiguration.repositories import InstituteRepository
from evaluation.management.register.utils import Utils

import firebase_admin

from django.contrib.auth import get_user_model

User = get_user_model()


def register_users(institute_name):
    institute = InstituteRepository.get_institute_by_name(institute_name)
    if not institute:
        raise ValueError(f"Institute not found - <{institute_name}>.")
    gd_wrapper = GDWrapper(institute.spreadsheet_id)

    sheet_users = gd_wrapper.get_sheet_as_json("data")

    for sheet_user in sheet_users:
        if "password" in sheet_user and sheet_user["password"] != "":
            continue

        email = sheet_user["email"]
        password = Utils.generate_random_password()
        firebase_id = None

        try:
            firebase_id = CustomAuth.create_user(email=email, password=password)
        except firebase_admin.auth.EmailAlreadyExistsError:
            firebase_id = CustomAuth.get_user_by_email(email)
            password = ""

        db_user, _created = User.objects.get_or_create(
            username=firebase_id, defaults={"email": email}
        )
        user_id = db_user.id

        UserProfileRepository.create_user_profile(user_id=user_id)

        UserProfileRepository.set_institute(user_id=user_id, institute=institute)
        UserProfileRepository.set_name(user_id, sheet_user["name"])
        UserProfileRepository.set_phone(user_id, sheet_user["phone"])
        UserProfileRepository.set_institute_roll_number(
            user_id, sheet_user["roll_number"]
        )
        UserProfileRepository.set_onboarding_complete(user_id)

        sheet_user["password"] = password

    gd_wrapper.update_sheet("data", sheet_users)
