import logging

from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)


class SendgridService:
    @staticmethod
    def _send_email(
        user_email,
        template_data,
        template_id,
    ):
        if settings.DEPLOYMENT_TYPE=="ECF":
            from_name="Earth Care Foundation"
            from_email="lms.noreply@theearthcarefoundation.org"
        else:
            from_name="Sakshm LMS"
            from_email=settings.DEFAULT_FROM_EMAIL
        message = Mail(
            from_email=(from_email, from_name),
            to_emails=user_email,
            is_multiple=True,
        )
        message.dynamic_template_data = template_data
        message.template_id = template_id

        try:
            sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
            response = sendgrid_client.send(message)
            logger.info(
                f"Request sent to sendgrid for sending email. User Email: {user_email}, Template ID: {template_id}. Response status code: ${str(response.status_code)}"
            )

        except Exception as e:
            # Log and re-raise the exception to get reported on sentry
            logger.error(
                f"Request failed to sendgrid for sending email. User Email: {user_email}, Template ID: {template_id}. Exception: {e}"
            )
            raise e

    @staticmethod
    def send_password_email(email, password):
        SendgridService._send_email(
            user_email=email,
            template_data={"email":email,"password": password},
            template_id=settings.PASSWORD_EMAIL_TEMPLATE_ID,
        )
