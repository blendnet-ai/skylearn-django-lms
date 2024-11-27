from django.core.management.base import BaseCommand
from evaluation.management.generate_status_sheet.index import generate_status_sheets


class Command(BaseCommand):
    help = "Generates and uploads status sheets on google drive"

    def handle(self, *args, **options):
        generate_status_sheets()
