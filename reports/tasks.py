from celery import shared_task
from django.utils import timezone
import logging  # {{ edit_1 }}
from .usecases import GenerateUserCourseReportsUseCase,DailyAggregationUsecase
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
# {{ edit_2 }}
logger = logging.getLogger(__name__)  # Setup logger
User = get_user_model()

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
    for user in student_users:
        generate_user_activites_aggregation.delay(user.id)

@shared_task(queue='reporting_queue') 
def generate_user_activites_aggregation(user_id):
    current_date = datetime.now().date()
    DailyAggregationUsecase.create_daily_aggregation_entries_for_user(user_id,current_date)
    


    
    
    
