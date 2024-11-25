import logging
from custom_auth.repositories import UserProfileRepository
from custom_auth.services.custom_auth_service import CustomAuth
from evaluation.management.generate_status_sheet.gd_wrapper import GDWrapper

from InstituteConfiguration.repositories import InstituteRepository
from evaluation.management.register.utils import Utils

import firebase_admin

from django.contrib.auth import get_user_model
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from django.conf import settings

logger = logging.getLogger(__name__)

User = get_user_model()


def send_email(user_email, password):
    message = Mail(
        from_email=("admin@sakshm.com", "Sakshm"),
        to_emails=user_email,
        is_multiple=True,
    )
    message.dynamic_template_data = {
        "username": user_email,
        "password": password,
    }

    message.template_id = settings.CREDS_EMAIL_TEMPLATE_ID

    try:
        sendgrid_client = SendGridAPIClient(settings.SENDGRID_KEY)
        response = sendgrid_client.send(message)
        logger.log_message(
            f"Request sent to sendgrid for sending email. Response status code: ${str(response.status_code)}"
        )
    except Exception as e:
        logger.log_message(f"Request failed to sendgrid for sending email: {e}")


def send_email_to_registerd_users():
    institue = InstituteRepository.get(id=2)
    gd_wrapper = GDWrapper(institue.spreadsheet_id)

    sheet_users = gd_wrapper.get_sheet_as_json("data")

    for sheet_user in sheet_users:
        if "password" not in sheet_user or sheet_user["password"] == "":
            continue

        email = sheet_user["email"]
        password = sheet_user["password"]

        send_email(email, password)
