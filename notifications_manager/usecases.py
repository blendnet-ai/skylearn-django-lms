from django.utils import timezone
from notifications.services import NotificationService
from notifications.repositories import NotificationIntentRepository
from notifications_manager.repositories import NotificationTemplateRepository
from notifications.models import NotificationIntent
from notifications.tasks import send_immediate_notifications
from meetings.repositories import MeetingRepository, AttendaceRecordRepository
from meetings.usecases import MeetingAttendanceUseCase
from accounts.repositories import UserRepository, StudentRepository
from evaluation.repositories import AssessmentGenerationConfigRepository
from course.repositories import BatchRepository
from datetime import datetime, timedelta
import pytz
import logging
from django.conf import settings
from notifications_manager.models import NotificationConfig
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

utc_tz = pytz.UTC
indian_tz = pytz.timezone("Asia/Kolkata")


class NotificationManagerUsecase:
    """Main usecase class with simplified interface"""
    
    @staticmethod
    def create_notification_intent(
        message_template,
        variables,
        user_ids,
        medium,
        notification_type,
        reference_id=None,
        scheduled_at=None,
    ):
        return NotificationIntentRepository.create_intent(
            message_template=message_template,
            variables=variables,
            user_ids=user_ids,
            medium=medium,
            scheduled_at=scheduled_at,
            notification_type=notification_type,
            reference_id=reference_id,
        )

    @staticmethod
    def schedule_notification(
        reference_id: Optional[str],
        template: str,
        variables: List[Dict],
        user_ids: List[int],
        medium: str,
        scheduled_at: datetime,
        notification_type: str,
    ) -> None:
        existing_intent = NotificationIntentRepository.get_existing_intent(
            reference_id=reference_id,
            notification_type=notification_type,
            medium=medium,
            scheduled_at=scheduled_at
        )

        if existing_intent is None or notification_type == "batch_message":
            NotificationManagerUsecase.create_notification_intent(
                message_template=template,
                variables=variables,
                user_ids=user_ids,
                medium=medium,
                scheduled_at=scheduled_at.astimezone(utc_tz),
                notification_type=notification_type,
                reference_id=reference_id,
            )

    @staticmethod
    def schedule_meeting_notifications():
        current_time = datetime.now(pytz.timezone("Asia/Kolkata"))
        twenty_four_hours = current_time + timedelta(hours=24)

        upcoming_meetings = MeetingRepository.get_meetings_in_time_range(
            twenty_four_hours.date(), twenty_four_hours.date()
        )

        # Get notification configs from database
        meeting_configs = NotificationConfig.objects.filter(
            notification_type__startswith='meeting_'
        )

        for meeting in upcoming_meetings:
            participants = meeting.get_participants
            
            # Prepare common variables
            variables = NotificationManagerUsecase._prepare_meeting_variables(meeting, participants)
            user_ids = [participant.id for participant in participants]

            # Schedule notifications based on configs
            for config in meeting_configs:
                meeting_time = datetime.combine(meeting.start_date, meeting.start_time.time())
                meeting_time = indian_tz.localize(meeting_time)
                
                # Calculate scheduled_at based on hours_before and minutes_before
                scheduled_at = meeting_time
                if config.hours_before:
                    scheduled_at -= timedelta(hours=config.hours_before)
                if config.minutes_before:
                    scheduled_at -= timedelta(minutes=config.minutes_before)

                # Schedule for each medium
                for medium in config.mediums:
                    template = NotificationTemplateRepository.get_template_by_type(
                        config.template_types[medium]
                    )
                    if not template:
                        logger.error(f"Template not found: {config.template_types[medium]}")
                        continue

                    NotificationManagerUsecase.schedule_notification(
                        meeting.id,
                        template.body,
                        variables,
                        user_ids,
                        medium,
                        scheduled_at,
                        config.notification_type,
                    )

    @staticmethod
    def _prepare_meeting_variables(meeting, participants):
        """Helper method to prepare variables for meeting notifications"""
        variables = []
        formatted_datetime = NotificationManagerUsecase._format_meeting_datetime(meeting)
        
        for participant in participants:
            variables.append({
                "title": meeting.title,
                "course": meeting.course.title,
                "participant_name": participant.get_full_name,
                "date_time": formatted_datetime,
                "class_link": MeetingAttendanceUseCase.get_joining_url(
                    participant.id, meeting.id
                ),
                "email_subject": f"Reminder: {'Upcoming Class Scheduled for'} \"{meeting.course.title}\""
            })
        return variables

    @staticmethod
    def _format_meeting_datetime(meeting):
        combined_datetime = datetime.combine(meeting.start_date, meeting.start_time.time())
        combined_datetime_ist = indian_tz.localize(combined_datetime)
        return combined_datetime_ist.strftime("%d %b %Y %H:%M")

    @staticmethod
    def schedule_missed_lecture_notifications():
        """
        Check for completed meetings with recordings and schedule notifications
        for absent students
        """
        logger.info("Checking for missed lecture notifications to schedule")

        # Get completed meetings with recordings that haven't sent notifications
        meetings = (
            MeetingRepository.get_completed_meetings_in_past_24_hours_with_recordings()
        )

        for meeting in meetings:
            try:
                # Get recording URL from metadata
                recording_url = None
                if meeting.blob_url != "" and meeting.blob_url is not None:
                    recording_url = f"{settings.FRONTEND_BASE_URL}/recordings?recordingId={meeting.id}"

                if not recording_url:
                    logger.warning(
                        f"No valid recording URL found for meeting {meeting.id}"
                    )
                    continue

                # Get absent users
                absent_users = AttendaceRecordRepository.get_absent_users_for_meeting(
                    meeting.id
                )

                if not absent_users:
                    logger.info(f"No absent users found for meeting {meeting.id}")
                    continue

                # Get user details

                # Prepare notification data
                variables = []
                user_ids = []

                for user in absent_users:
                    user_ids.append(user.user_id.id)
                    variables.append(
                        {
                            "participant_name": user.user_id.get_full_name,
                            "course_name": meeting.course.title,
                            "meeting_title": meeting.title,
                            "recording_link": recording_url,
                            "email_subject": "You Missed a Class – Recording Available"
                        }
                    )

                # Get notification template
                template_telegram = NotificationTemplateRepository.get_template_by_type(
                    "missed_lecture_telegram"
                )
                template_email = NotificationTemplateRepository.get_template_by_type(
                    "missed_lecture_email"
                )

                if not template_email or not template_telegram:
                    logger.error("Missed lecture notification template not found")
                    continue

                NotificationManagerUsecase.schedule_notification(
                    meeting.id,
                    template_telegram.body,
                    variables,
                    user_ids,
                    "telegram",
                    datetime.now(utc_tz),
                    "missed_lecture",
                )
                NotificationManagerUsecase.schedule_notification(
                    meeting.id,
                    template_email.body,
                    variables,
                    user_ids,
                    "email",
                    datetime.now(utc_tz),
                    "missed_lecture",
                )

                logger.info(
                    f"Scheduled missed lecture notifications for meeting {meeting.id}"
                )

            except Exception as e:
                logger.error(
                    f"Error scheduling missed lecture notifications for meeting {meeting.id}: {str(e)}"
                )

    @staticmethod
    def schedule_inactive_users_notifications():
        try:
            inactive_users = UserRepository.get_inactive_users(7)
            template_user_inactive_7_days_email = (
                NotificationTemplateRepository.get_template_by_type(
                    "user_inactivity_7_days_email"
                )
            )
            template_user_inactive_7_days_telegram = (
                NotificationTemplateRepository.get_template_by_type(
                    "user_inactivity_7_days_telegram"
                )
            )
            variables = []
            user_ids = []
            for user in inactive_users:
                user_ids.append(user.id)

                variables.append(
                    {"participant_name": user.get_full_name, "url": f"{settings.FRONTEND_BASE_URL}", "email_subject": "It's Time to Get Back to Learning!"}
                )

            NotificationManagerUsecase.schedule_notification(
                None,
                template_user_inactive_7_days_email.body,
                variables,
                user_ids,
                "email",
                datetime.now(utc_tz),
                "user_inactive_7_days",
            )

            NotificationManagerUsecase.schedule_notification(
                None,
                template_user_inactive_7_days_telegram.body,
                variables,
                user_ids,
                "telegram",
                datetime.now(utc_tz),
                "user_inactive_7_days",
            )
            logger.info(f"Scheduled inactive notification for users")

        except Exception as e:
            logger.error(f"Error scheduling inactive user notifications: {str(e)}")

    def schedule_assessment_notifications():
        logger.info("Checking for pending assessments to schedule")
        students = StudentRepository.get_all_students()
        template_pending_assessments_email = (
            NotificationTemplateRepository.get_template_by_type(
                "assessments_pending_email"
            )
        )
        template_pending_assessments_telegram = (
            NotificationTemplateRepository.get_template_by_type(
                "assessments_pending_telegram"
            )
        )
        user_ids = []
        variables = []
        for student in students:
            assessments = (
                AssessmentGenerationConfigRepository.fetch_pending_assessments_for_user(
                    student.student_id
                )
            )
            if len(assessments) > 0:
                user_ids.append(student.student_id)
                variables.append(
                    {
                        "course_name": assessments[0].modules.first().course.title,
                        "assessment_link": f"{settings.FRONTEND_BASE_URL}/modules/{assessments[0].modules.first().course.title}?courseId={assessments[0].modules.first().course.id}".replace(' ','-'),
                        "email_subject": "Reminder: Complete Your Assessment Today! 🎯"
                    }
                )
        NotificationManagerUsecase.schedule_notification(
            None,
            template_pending_assessments_email.body,
            variables,
            user_ids,
            "email",
            datetime.now(utc_tz),
            "pending_assessment",
        )
        NotificationManagerUsecase.schedule_notification(
            None,
            template_pending_assessments_telegram.body,
            variables,
            user_ids,
            "telegram",
            datetime.now(utc_tz),
            "assessment",
        )
    
    @staticmethod
    def send_immediate_notification(
        message_template,
        variables,
        user_ids,
        medium,
        notification_type,
        reference_id=None,
    ):
        try:
            # Create an intent with immediate timing
            intent = NotificationIntentRepository.create_intent(
                message_template=message_template,
                variables=variables,
                user_ids=user_ids,
                medium=medium,
                scheduled_at=timezone.now(),
                notification_type=notification_type,
                reference_id=reference_id,
                timing_type='immediate'
            )
            
            # Process the intent immediately using NotificationService
            from notifications.services import NotificationService
            send_immediate_notifications.delay(intent.id)
            
            logger.info(f"Immediate notification sent successfully for intent {intent.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending immediate notification: {str(e)}")
            raise

