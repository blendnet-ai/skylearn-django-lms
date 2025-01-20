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
        return NotificationIntent.objects.filter(processed=False, scheduled_at__lte=scheduled_time)
    
    def get_intent_by_id(id):
        return NotificationIntent.objects.filter(id=id).first()


class NotificationRecordRepository:
    @staticmethod
    def create_record(intent, user, message, medium):
        record, created = NotificationRecord.objects.get_or_create(
            intent=intent,
            user=user,
            defaults={
                'message': message,
                'medium': medium,
                'sent': False
            }
        )
        if not created:
            if record.sent:
                logger.info(f"Notification already sent for intent_id={intent.id} and user_id={user.user_id}")
                return None
            logger.info(f"Found existing unsent notification record for intent_id={intent.id} and user_id={user.user_id}")
        return record

    @staticmethod
    def mark_record_as_sent(record, sent_status):
        record.sent = sent_status
        record.sent_at = timezone.now()
        record.save()
