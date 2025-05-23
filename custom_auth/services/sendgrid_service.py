import logging

from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from sendgrid.helpers.mail import Mail, Email, To, Cc

logger = logging.getLogger(__name__)


class SendgridService:
    @staticmethod
    def _send_email(
        user_email,
        template_data,
        template_id,
        cc_emails=None,
    ):
        if settings.DEPLOYMENT_TYPE == "ECF":
            from_name = "Earth Care Foundation"
            from_email = "lms.noreply@theearthcarefoundation.org"
        else:
            from_name = "Sakshm LMS"
            from_email = settings.DEFAULT_FROM_EMAIL
        message = Mail(
            from_email=(from_email, from_name),
            to_emails=user_email,
            is_multiple=True,
        )
        if cc_emails is not None:
            message.add_cc(cc_emails)
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
        cc_email = (
            settings.PASSWORD_CC_EMAIL
            if hasattr(settings, "PASSWORD_CC_EMAIL")
            else None
        )
        SendgridService._send_email(
            user_email=email,
            template_data={"email": email, "password": password},
            template_id=settings.PASSWORD_EMAIL_TEMPLATE_ID,
            cc_emails=[Cc(cc_email)] if cc_email else None,
        )
