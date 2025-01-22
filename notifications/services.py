from abc import ABC, abstractmethod
from django.template import Template, Context
from django.conf import settings
from django.core.mail import send_mass_mail
import requests
from .repositories import UserRepository, NotificationRecordRepository, NotificationIntentRepository
from .providers import EmailNotificationProvider, TelegramNotificationProvider
import logging
from .exceptions import NotificationIntentProcessingError
from .models import NotificationIntent

logger = logging.getLogger(__name__)

class NotificationService:
    _providers = {
        'email': EmailNotificationProvider(),
        'telegram': TelegramNotificationProvider()
    }

    @staticmethod
    def create_intent(message_template, variables, user_ids, medium, scheduled_at):
        if len(variables) != len(user_ids):
            raise ValueError("The number of variables must match the number of user IDs.")
        
        return NotificationIntentRepository.create_intent(
            message_template=message_template,
            variables=variables,  # Pass the list of dicts
            user_ids=user_ids,
            medium=medium,
            scheduled_at=scheduled_at
        )
    
    @staticmethod
    def process_intent(intent_id):
        try:
            intent = NotificationIntentRepository.get_intent_by_id(intent_id)
            
            if intent.state == NotificationIntent.State.PICKED:
                logger.info(f"Intent {intent_id} is in PICKED state")
                return
            
            NotificationIntentRepository.mark_intent_as_processing(intent)
             
            # Get users and prepare notifications
            existing_users = UserRepository.get_users_by_ids(intent.user_ids)
            
           
            
            # Create mapping of user_id to user object
            user_map = {str(user.user_id): user.user for user in existing_users}
            user_telegram_map = {str(user.user_id): user.telegram_chat_id for user in existing_users}

            provider = NotificationService._providers.get(intent.medium)
            if not provider:
                raise ValueError(f"Unsupported notification medium: {intent.medium}")

            records = []
            messages_data = []
            skipped_users = []
            
            # Process users and create notifications
            for user_id, user_variables in zip(intent.user_ids, intent.variables):
                # Skip if user doesn't exist
                if str(user_id) not in user_map:
                    skipped_users.append({
                        'user_id': user_id,
                        'variables': user_variables,
                        'reason': 'User not found in database'
                    })
                    logger.warning(
                        f"Skipping notification for user_id={user_id}. "
                        f"Reason: User not found in database. "
                        f"Variables that would have been used: {user_variables}"
                    )
                    continue
                
                user = user_map[str(user_id)]
                telegram_chat_id = user_telegram_map[str(user_id)]
                
                rendered_message = NotificationService.render_message(
                    intent.message_template,
                    user_variables
                )
                
                record = NotificationRecordRepository.create_record(
                    intent=intent,
                    user=user,
                    message=rendered_message, 
                    medium=intent.medium
                )
                
                if record is None:
                    skipped_users.append({
                        'user_id': user_id,
                        'variables': user_variables,
                        'reason': 'Notification already sent'
                    })
                    logger.info(f"Skipping already sent notification for user_id={user_id}")
                    continue
                
                records.append(record)
                recipient_id = user.email if intent.medium == 'email' else telegram_chat_id
                message_data = {
                    'record_id': record.record_id,
                    'recipient': recipient_id,
                    'message': rendered_message,
                    'variables': user_variables
                }
                messages_data.append(message_data)
            
            # Log summary of skipped users
            if skipped_users:
                logger.info(
                    f"Notification intent {intent_id} completed with {len(skipped_users)} skipped users. "
                    f"Total users processed: {len(messages_data)}. "
                    f"Skipped users summary: {skipped_users}"
                )
            
            # Send notifications if we have valid messages
            if messages_data:
                sent_status = provider.send_message(messages_data)
                
                record_map = {record.record_id: record for record in records}
                
                for status in sent_status:
                    record_id = status['record_id']
                    success = status['success']
                    error = status.get('error')
                    
                    record = record_map.get(record_id)
                    if record:
                        NotificationRecordRepository.mark_record_as_sent(record, success,error)
            
            NotificationIntentRepository.mark_intent_as_completed(intent)
            NotificationIntentRepository.mark_intent_as_processed(intent)
            
        except Exception as e:
            logger.error(f"Failed to process notification intent {intent_id}: {str(e)}")
            if intent:
                NotificationIntentRepository.mark_intent_as_failed(intent, str(e))
            raise NotificationIntentProcessingError(str(e))
    
    @staticmethod
    def render_message(template_str, variables):
        # Check if the input is a template or a plain string
        if "{{" not in template_str and "{%" not in template_str:
            # Directly return plain string without rendering
            return template_str
        template = Template(template_str)
        context = Context({**variables})
        return template.render(context)
    
    def send_immediate_notification(intent_id):
        intent = NotificationIntentRepository.get_intent_by_id(intent_id)
        NotificationService.process_intent(intent_id)
