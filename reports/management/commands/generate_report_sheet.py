import logging
from django.core.management.base import BaseCommand
from evaluation.management.generate_status_sheet.institute_sheet_generator import generate_global_sheet
from reports.management.generate_report_sheet.report_sheet_generator import report_sheet_generator

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Generates and uploads report sheets on Google Drive"

    def handle(self, *args, **options):
        try:
            report_sheet_generator()
        except Exception as e:
            logger.exception("An error occurred while generating the global sheet.")

