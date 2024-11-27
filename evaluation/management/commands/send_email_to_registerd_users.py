from django.core.management.base import BaseCommand
from evaluation.management.register.send_email_to_registerd_users import (
    send_email_to_registerd_users,
)


class Command(BaseCommand):
    help = "Script to send creds to user from a google sheet"

    def handle(self, *args, **options):
        send_email_to_registerd_users()
