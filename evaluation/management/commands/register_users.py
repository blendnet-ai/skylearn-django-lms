from django.core.management.base import BaseCommand
from evaluation.management.register.register_users import register_users


class Command(BaseCommand):
    help = "Script to register users from a google sheet"

    def add_arguments(self, parser):
        parser.add_argument(
            '--institute_name',
            type=str,
            help='The name of the institute',
            required=True
        )

    def handle(self, *args, **options):
        institute_name = options["institute_name"]
        register_users(institute_name=institute_name)
