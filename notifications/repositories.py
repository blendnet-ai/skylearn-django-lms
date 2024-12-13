from .models import UserInfo, NotificationIntent, NotificationRecord
from django.utils import timezone

class UserRepository:
    @staticmethod
    def get_user_by_id(user_id):
        return UserInfo.objects.get(user_id=user_id)

    @staticmethod
    def get_users_by_ids(user_ids):
        return UserInfo.objects.filter(user_id__in=user_ids)


class NotificationIntentRepository:
    @staticmethod
    def get_existing_intent(reference_id, notification_type, medium):
        return NotificationIntent.objects.filter(
            reference_id=reference_id,
            notification_type=notification_type,
            processed=False,
            medium=medium
        ).first()

    @staticmethod
    def create_intent(message_template, variables, user_ids, medium, 
                     notification_type, reference_id=None, scheduled_at=None):
        # Check for duplicate intent if reference_id is provided
        if reference_id:
            existing_intent = NotificationIntentRepository.get_existing_intent(
                reference_id=reference_id,
                notification_type=notification_type,
                medium=medium
            )
            if existing_intent:
                return existing_intent

        return NotificationIntent.objects.create(
            message_template=message_template,
            variables=variables,
            user_ids=user_ids,
            medium=medium,
            scheduled_at=scheduled_at,
            notification_type=notification_type,
            reference_id=reference_id
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
    def create_record(intent, user, message,medium):
        return NotificationRecord.objects.create(
            intent=intent,
            user=user,
            message=message,
            medium=medium
        )

    @staticmethod
    def mark_record_as_sent(record,sent_status):
        record.sent = sent_status
        record.sent_at = timezone.now()
        record.save()
