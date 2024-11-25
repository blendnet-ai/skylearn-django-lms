import logging
from django.core.management.base import BaseCommand
from evaluation.management.generate_status_sheet.institute_sheet_generator import generate_global_sheet

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Generates and uploads status sheets on Google Drive"

    def handle(self, *args, **options):
        try:
            generate_global_sheet()
        except Exception as e:
            logger.exception("An error occurred while generating the global sheet.")

