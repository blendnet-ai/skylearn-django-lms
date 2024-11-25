import logging
from django.core.management.base import BaseCommand
from evaluation.management.generate_status_sheet.institute_sheet_generator import generate_institute_sheets

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Generates and uploads status sheets on Google Drive"

    def handle(self, *args, **options):
        try:
            generate_institute_sheets()
        except Exception as e:
            logger.exception("An error occurred while generating and uploading institute sheets.")
