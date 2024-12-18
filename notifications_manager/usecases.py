from django.utils import timezone
from notifications.services import NotificationService
from notifications.repositories import NotificationIntentRepository
from notifications_manager.repositories import NotificationTemplateRepository
from notifications.models import NotificationIntent
from meetings.repositories import MeetingRepository, AttendaceRecordRepository
from accounts.repositories import UserRepository
from datetime import datetime, timedelta
import pytz
import logging

logger = logging.getLogger(__name__)

utc_tz = pytz.UTC
indian_tz = pytz.timezone('Asia/Kolkata')

class NotificationManagerUsecase:
    @staticmethod
    def create_notification_intent(message_template, variables, user_ids, medium, 
                                 notification_type, reference_id=None, scheduled_at=None):
        return NotificationIntentRepository.create_intent(
            message_template=message_template,
            variables=variables,
            user_ids=user_ids,
            medium=medium,
            scheduled_at=scheduled_at,
            notification_type=notification_type,
            reference_id=reference_id
        )

    @staticmethod
    def schedule_notification(reference_id, template, variables, user_ids, medium, scheduled_at, notification_type):
        existing_intent = NotificationIntentRepository.get_existing_intent(
            reference_id=reference_id,
            notification_type=notification_type,
            medium=medium
        )
        
        if existing_intent is None:
            NotificationManagerUsecase.create_notification_intent(
                message_template=template,
                variables=variables,
                user_ids=user_ids,
                medium=medium,
                scheduled_at=scheduled_at.astimezone(utc_tz),
                notification_type=notification_type,
                reference_id=reference_id
            )

    @staticmethod
    def schedule_meeting_notifications():
        # Get the current time in Indian timezone
        current_time = datetime.now(pytz.timezone('Asia/Kolkata'))
        twenty_four_hours = current_time + timedelta(hours=24)
        
        # Fetch meetings happening in the next 24 hours
        upcoming_meetings = MeetingRepository.get_meetings_in_time_range(current_time, twenty_four_hours)

        # Get templates from database
        template_24h_email = NotificationTemplateRepository.get_template_by_type('meeting_24h_email')
        template_30m_email = NotificationTemplateRepository.get_template_by_type('meeting_30m_email')
        template_24h_telegram = NotificationTemplateRepository.get_template_by_type('meeting_24h_telegram')
        template_30m_telegram = NotificationTemplateRepository.get_template_by_type('meeting_30m_telegram')
        
        if not template_24h_email or not template_30m_email or not template_24h_telegram or not template_30m_telegram:
            logger.error("Notification templates not found")
            return

        for meeting in upcoming_meetings:
            participants = meeting.get_participants()
            
            # Prepare meeting details
            course_name = meeting.course.title
            title = meeting.title
            start_date = meeting.start_date
            start_time = meeting.start_time.time()
            class_link = meeting.link
            
            # Create localized datetime
            combined_datetime = datetime.combine(start_date, start_time)
            combined_datetime_ist = indian_tz.localize(combined_datetime)
            formatted_datetime = combined_datetime_ist.strftime("%d %b %Y %H:%M")

            variables = []
            user_ids = []

            # Prepare notification data for each participant
            for participant in participants:
                participant_name = participant.get_full_name
                user_ids.append(participant.id)
                variables.append({
                    "title": title,
                    "course": course_name,
                    "participant_name": participant_name,
                    "date_time": formatted_datetime,
                    "class_link": class_link
                })

            # Schedule 24-hour notification
            scheduled_at_24h = combined_datetime_ist - timedelta(hours=24)
            NotificationManagerUsecase.schedule_notification(
                meeting.id,
                template_24h_email.body,
                variables,
                user_ids,
                'email',
                scheduled_at_24h,
                'meeting_24h'
            )
            NotificationManagerUsecase.schedule_notification(
                meeting.id,
                template_24h_telegram.body,
                variables,
                user_ids,
                'telegram',
                scheduled_at_24h,
                'meeting_24h'
            )

            # Schedule 30-minute notification
            scheduled_at_30m = combined_datetime_ist - timedelta(minutes=30)
            NotificationManagerUsecase.schedule_notification(
                meeting.id,
                template_30m_email.body,
                variables,
                user_ids,
                'email',
                scheduled_at_30m,
                'meeting_30m'
            )
            NotificationManagerUsecase.schedule_notification(
                meeting.id,
                template_30m_telegram.body,
                variables,
                user_ids,
                'telegram',
                scheduled_at_30m,
                'meeting_30m'
            )
            
    @staticmethod
    def schedule_missed_lecture_notifications():
        """
        Check for completed meetings with recordings and schedule notifications
        for absent students
        """
        logger.info("Checking for missed lecture notifications to schedule")

        # Get completed meetings with recordings that haven't sent notifications
        meetings = MeetingRepository.get_completed_meetings_in_past_24_hours_with_recordings()
        
        for meeting in meetings:
            try:
                # Get recording URL from metadata
                recording_url = None
                if meeting.blob_url != '' and meeting.blob_url is not None:
                    recording_url = f"http://20.244.100.109:5001/recordings?recordingId={meeting.id}"
                    
                
                if not recording_url:
                    logger.warning(f"No valid recording URL found for meeting {meeting.id}")
                    continue
                
                # Get absent users
                absent_users = AttendaceRecordRepository.get_absent_users_for_meeting(meeting.id)
                
                if not absent_users:
                    logger.info(f"No absent users found for meeting {meeting.id}")
                    continue
                
                # Get user details
                
                # Prepare notification data
                variables = []
                user_ids = []
                
                for user in absent_users:
                    user_ids.append(user.user_id.id)
                    variables.append({
                        'participant_name': user.user_id.get_full_name,
                        'course_name': meeting.title,
                        'recording_link': recording_url
                    })
                
                # Get notification template
                template_email = NotificationTemplateRepository.get_template_by_type('missed_lecture_telegram')
                template_telegram = NotificationTemplateRepository.get_template_by_type('missed_lecture_email')
                
                if not template_email or not template_telegram:
                    logger.error("Missed lecture notification template not found")
                    continue
                
                NotificationManagerUsecase.schedule_notification(meeting.id, template_telegram.body, variables, user_ids, 'telegram', datetime.now(utc_tz), 'missed_lecture')
                NotificationManagerUsecase.schedule_notification(meeting.id, template_email.body, variables, user_ids, 'email', datetime.now(utc_tz), 'missed_lecture')
                
                
                logger.info(f"Scheduled missed lecture notifications for meeting {meeting.id}")
                
            except Exception as e:
                logger.error(f"Error scheduling missed lecture notifications for meeting {meeting.id}: {str(e)}")

    @staticmethod
    def schedule_inactive_users_notifications():
        try:
            inactive_users=UserRepository.get_inactive_users(7)
            template_user_inactive_7_days_email=NotificationTemplateRepository.get_template_by_type('user_inactivity_7_days_email')
            template_user_inactive_7_days_telegram=NotificationTemplateRepository.get_template_by_type('user_inactivity_7_days_telegram')
            variables=[]
            user_ids=[]
            for user in inactive_users:
                user_ids.append(user.id)

                variables.append({
                    'participant_name': user.get_full_name,
                    'url': 'https://www.google.com'
                })
                
            NotificationManagerUsecase.schedule_notification(
                None,
                template_user_inactive_7_days_email.body,
                variables,
                user_ids,
                'email',
                datetime.now(utc_tz),
                'user_inactive_7_days'
            )
            
            NotificationManagerUsecase.schedule_notification(
                None,
                template_user_inactive_7_days_telegram.body,
                variables,
                user_ids,
                'telegram',
                datetime.now(utc_tz),
                'user_inactive_7_days'
            )
            logger.info(f"Scheduled inactive notification for user {user.id}")
                
        except Exception as e:
            logger.error(f"Error scheduling inactive user notifications: {str(e)}")
        
        