# remove
import threading
from datetime import datetime
from django.contrib.auth import get_user_model
from django.conf import settings
from core.utils import send_html_email
import uuid


def generate_password():
    return get_user_model().objects.make_random_password()


def generate_student_id():
    # Add random UUID to ensure uniqueness
    random_id = str(uuid.uuid4())[:8]
    return f"{settings.STUDENT_ID_PREFIX}-{random_id}"


def generate_lecturer_id():
    # Generate a username based on first and last name and registration date
    random_id = str(uuid.uuid4())[:8]
    return f"{settings.LECTURER_ID_PREFIX}-{random_id}"


def generate_student_credentials():
    return generate_student_id(), generate_password()


def generate_lecturer_credentials():
    return generate_lecturer_id(), generate_password()


class EmailThread(threading.Thread):
    def __init__(self, subject, recipient_list, template_name, context):
        self.subject = subject
        self.recipient_list = recipient_list
        self.template_name = template_name
        self.context = context
        threading.Thread.__init__(self)

    def run(self):
        send_html_email(
            subject=self.subject,
            recipient_list=self.recipient_list,
            template=self.template_name,
            context=self.context,
        )


def send_new_account_email(user, password):
    if user.is_student:
        template_name = "accounts/email/new_student_account_confirmation.html"
    else:
        template_name = "accounts/email/new_lecturer_account_confirmation.html"
    email = {
        "subject": "Your SkyLearn account confirmation and credentials",
        "recipient_list": [user.email],
        "template_name": template_name,
        "context": {"user": user, "password": password},
    }
    EmailThread(**email).start()
