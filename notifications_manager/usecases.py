from django.utils import timezone
from notifications.services import NotificationService
from notifications.repositories import NotificationIntentRepository
from notifications.models import NotificationIntent
from meetings.repositories import MeetingRepository
from datetime import datetime, timedelta
import pytz

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
    def schedule_notification(meeting, template, variables, user_ids, medium, scheduled_at, notification_type):
        existing_intent = NotificationIntentRepository.get_existing_intent(
            reference_id=meeting.id,
            notification_type=notification_type,
            medium=medium
        )
        
        if scheduled_at > datetime.now(pytz.timezone('Asia/Kolkata')) and existing_intent is None:
            NotificationManagerUsecase.create_notification_intent(
                message_template=template,
                variables=variables,
                user_ids=user_ids,
                medium=medium,
                scheduled_at=scheduled_at.astimezone(utc_tz),
                notification_type=notification_type,
                reference_id=meeting.id
            )

    @staticmethod
    def schedule_meeting_notifications():
        # Get the current time in Indian timezone
        current_time = datetime.now(pytz.timezone('Asia/Kolkata'))
        twenty_four_hours = current_time + timedelta(hours=24)
        
        # Fetch meetings happening in the next 24 hours
        upcoming_meetings = MeetingRepository.get_meetings_in_time_range(current_time, twenty_four_hours)

        live_reminder_before_24_hour_template = (
            "Subject: Reminder: Upcoming Class Scheduled for \"{{course}}\"\n\n"
            "Dear {{participant_name}},\n\n"
            "This is a gentle reminder about your upcoming class for \"{{course}}\" course.\n\n"
            "• Topic: {{title}}\n"
            "• Date and Time: {{date_time}}\n"
            "• Class Link: {{class_link}}\n\n"
            "Please make sure to be prepared and ready to join the session.\n\n"
            "Looking forward to seeing you there!\n\n"
            "Best regards,\n"
            "Team Sakshm AI"
        )
        
        live_reminder_before_30_min_template = (
            "Reminder: Your class for \"{{course}}\" starts soon\n\n"
            "Dear {{participant_name}},\n\n"
            "This is a gentle reminder about your upcoming class for \"{{course}}\" course.\n\n"
            "• Topic: {{title}}\n"
            "• Date and Time: {{date_time}}\n"
            "• Class Link: {{class_link}}\n\n"
            "Please make sure to be prepared and ready to join the session.\n\n"
            "Looking forward to seeing you there!\n\n"
            "Best regards,\n"
            "Team Sakshm AI"
        )

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
                meeting,
                live_reminder_before_24_hour_template,
                variables,
                user_ids,
                'email',
                scheduled_at_24h,
                'meeting_24h'
            )
            NotificationManagerUsecase.schedule_notification(
                meeting,
                live_reminder_before_24_hour_template,
                variables,
                user_ids,
                'telegram',
                scheduled_at_24h,
                'meeting_24h'
            )

            # Schedule 30-minute notification
            scheduled_at_30m = combined_datetime_ist - timedelta(minutes=30)
            NotificationManagerUsecase.schedule_notification(
                meeting,
                live_reminder_before_30_min_template,
                variables,
                user_ids,
                'email',
                scheduled_at_30m,
                'meeting_30m'
            )
            NotificationManagerUsecase.schedule_notification(
                meeting,
                live_reminder_before_30_min_template,
                variables,
                user_ids,
                'telegram',
                scheduled_at_30m,
                'meeting_30m'
            )

    @staticmethod
    def schedule_inactive_users_notifications():
        pass
        