from celery import shared_task
from django.utils import timezone
import logging

from reports.management.generate_report_sheet.report_sheet_generator import report_sheet_generator
from .usecases import GenerateUserCourseReportsUseCase,DailyAggregationUsecase
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)  # Setup logger
User = get_user_model()

@shared_task(queue='reporting_queue')
def generate_report_sheet():
    report_sheet_generator()

@shared_task(queue='reporting_queue') 
def process_reports():
    student_users=User.objects.filter(is_student=True)
    for user in student_users:
        generate_student_report.delay(user.id)

@shared_task(queue='reporting_queue') 
def generate_student_report(user_id):
    current_date = datetime.now().date()
    GenerateUserCourseReportsUseCase.generate_report(user_id)
    logger.info(f"started daily report creation for user {user_id}")
    

@shared_task(queue='reporting_queue')
def process_aggregation():
    student_users=User.objects.filter(is_student=True)
    current_date = datetime.now().date()
    for user in student_users:
        generate_user_activites_aggregation.delay(user.id,current_date)

@shared_task(queue='reporting_queue') 
def generate_user_activites_aggregation(user_id,current_date):
    DailyAggregationUsecase.create_daily_aggregation_entries_for_user(user_id,current_date)
    


    
    
    
