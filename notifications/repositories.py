from .models import UserInfo, NotificationIntent, NotificationRecord
from django.utils import timezone
from channels.db import database_sync_to_async
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    @staticmethod
    def get_user_by_id(user_id):
        return UserInfo.objects.get(user_id=user_id)

    @staticmethod
    def get_users_by_ids(user_ids):
        return UserInfo.objects.filter(user_id__in=user_ids)
    
    @staticmethod
    @database_sync_to_async
    def add_user_info(user_id, email, telegram_chat_id):
        return UserInfo.objects.create(user_id=user_id, email=email, telegram_chat_id=telegram_chat_id)


class NotificationIntentRepository:
    @staticmethod
    def get_existing_intent(reference_id, notification_type, medium, scheduled_at):
        return NotificationIntent.objects.filter(
            reference_id=reference_id,
            notification_type=notification_type,
            processed=False,
            scheduled_at__date=scheduled_at.date(),
            medium=medium
        ).first()

    @staticmethod
    def create_intent(
        message_template, 
        variables, 
        user_ids, 
        medium, 
        notification_type, 
        reference_id=None, 
        scheduled_at=None,
        timing_type='scheduled'
    ):
        return NotificationIntent.objects.create(
            message_template=message_template,
            variables=variables,
            user_ids=user_ids,
            medium=medium,
            scheduled_at=scheduled_at,
            notification_type=notification_type,
            reference_id=reference_id,
            timing_type=timing_type
        )

    @staticmethod
    def get_pending_intents():
        return NotificationIntent.objects.filter(processed=False)

    @staticmethod
    def mark_intent_as_processed(intent):
        intent.processed = True
        intent.save()

    @staticmethod
    def get_pending_intents_by_time(scheduled_time):
        return NotificationIntent.objects.filter(
            processed=False,
            scheduled_at__lte=scheduled_time
        )
    
    @staticmethod
    def get_intent_by_id(id):
        return NotificationIntent.objects.filter(id=id).first()

    @staticmethod
    def mark_intent_as_picked(intent):
        intent.state = NotificationIntent.State.PICKED
        intent.save()
    
    @staticmethod
    def mark_intent_as_processing(intent):
        intent.state = NotificationIntent.State.PROCESSING
        intent.save()
    
    @staticmethod
    def mark_intent_as_completed(intent):
        intent.state = NotificationIntent.State.COMPLETED
        intent.processing_completed_at = timezone.now()
        intent.processed = True
        intent.save()
    
    @staticmethod
    def mark_intent_as_failed(intent, error_message):
        intent.state = NotificationIntent.State.FAILED
        intent.error_message = error_message
        intent.processing_completed_at = timezone.now()
        intent.processed = True
        intent.save()

    @staticmethod
    def delete_intents_by_reference(reference_id, notification_types):
        """
        Delete all notification intents for a given reference_id and notification types
        
        Args:
            reference_id: The reference ID (e.g., meeting_id)
            notification_types: List of notification types to delete
        """
        return NotificationIntent.objects.filter(
            reference_id=reference_id,
            notification_type__in=notification_types
        ).delete()

    @staticmethod
    def get_pending_intents_by_reference(reference_id, notification_types):
        """
        Get pending notification intents for a given reference_id and notification types
        
        Args:
            reference_id: The reference ID (e.g., meeting_id)
            notification_types: List of notification types to fetch
        """
        return NotificationIntent.objects.filter(
            reference_id=reference_id,
            notification_type__in=notification_types,
            state='pending'
        )

    @staticmethod
    def update_intent_schedule(intent_id, scheduled_at):
        """
        Update the scheduled time for a notification intent
        
        Args:
            intent_id: ID of the intent to update
            scheduled_at: New scheduled datetime
        """
        NotificationIntent.objects.filter(id=intent_id).update(
            scheduled_at=scheduled_at
        )


class NotificationRecordRepository:
    @staticmethod
    def create_record(intent, user, message, medium):
        record, created = NotificationRecord.objects.get_or_create(
            intent=intent,
            user=user,
            medium=medium,
            defaults={
                'message': message
            }
        )
        if not created:
            if record.sent:
                logger.info(f"Notification already sent for intent_id={intent.id} and user_id={user.id}")
                return None
            logger.info(f"Found existing unsent notification record for intent_id={intent.id} and user_id={user.id}")
        return record

    @staticmethod
    def mark_record_as_sent(record, success,error):
        record.sent = success
        record.error=error
        record.sent_at = timezone.now()
        record.save()
