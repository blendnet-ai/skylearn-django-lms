from abc import ABC, abstractmethod
from django.template import Template, Context
from django.conf import settings
from django.core.mail import send_mass_mail
import requests
from .repositories import UserRepository, NotificationRecordRepository, NotificationIntentRepository
from .providers import EmailNotificationProvider, TelegramNotificationProvider
import logging

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
        intent = NotificationIntentRepository.get_intent_by_id(intent_id)
        users = UserRepository.get_users_by_ids(intent.user_ids)
        provider = NotificationService._providers.get(intent.medium)
        
        if not provider:
            raise ValueError(f"Unsupported notification medium: {intent.medium}")

        records = []
        messages_data = []  # Will store message data for each recipient
        
        for user, user_variables in zip(users, intent.variables):
            logger.info(f"Rendering message for user {user.email} with variables: {user_variables}")
            rendered_message = NotificationService.render_message(
                intent.message_template,
                user_variables
            )
            
            record = NotificationRecordRepository.create_record(
                intent=intent,
                user=user.user,
                message=rendered_message,
                medium=intent.medium
            )
            records.append(record)
            
            # Create message data dictionary
            recipient_id = user.email if intent.medium == 'email' else user.telegram_chat_id
            message_data = {
                'recipient': recipient_id,
                'message': rendered_message,
                'variables': user_variables  # Include original variables for additional customization
            }
            messages_data.append(message_data)
        
        # Send notifications using the appropriate provider with message data
        sent_status = provider.send_message(messages_data)
        
        # Update records
        for record in records:
            NotificationRecordRepository.mark_record_as_sent(record, sent_status)
        
        NotificationIntentRepository.mark_intent_as_processed(intent)

    @staticmethod
    def render_message(template_str, variables):
        template = Template(template_str)
        context = Context({**variables})
        return template.render(context)
    
    def send_immediate_notification(intent_id):
        intent = NotificationIntentRepository.get_intent_by_id(intent_id)
        NotificationService.process_intent(intent_id)
