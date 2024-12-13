from django.template import Template, Context
from django.conf import settings
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import requests
import json
from .repositories import UserRepository, NotificationRecordRepository, NotificationIntentRepository
#from mailjet_rest import Client  # Import Mailjet client
from django.core.mail import send_mass_mail

class NotificationService:
    @staticmethod
    def create_intent(message_template, variables, user_ids, medium, scheduled_at):
        # Ensure variables is a list of dictionaries corresponding to user_ids
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
        user_ids = intent.user_ids
        users = UserRepository.get_users_by_ids(user_ids)
        medium=intent.medium
        if medium == 'email':
            # Batch process all emails
            email_messages = []
            records = []
            
            # First create all records and render messages
            for user, user_variables in zip(users, intent.variables):
                rendered_message = NotificationService.render_message(
                    intent.message_template,
                    user_variables
                )
                
                record = NotificationRecordRepository.create_record(
                    intent=intent,
                    user=user.user,
                    message=rendered_message,
                    medium=medium
                )
                records.append(record)
                email_messages.append((user.email, rendered_message))
        
            # Send all emails in bulk with personalized messages
            if email_messages:
                sent_status = NotificationService.send_email(email_messages)
                
                # Update all records with the send status
                for record in records:
                    NotificationRecordRepository.mark_record_as_sent(record, sent_status)
        
        else:
            # Process other mediums (like Telegram) individually
            for user, user_variables in zip(users, intent.variables):
                rendered_message = NotificationService.render_message(
                    intent.message_template,
                    user_variables
                )
                
                record = NotificationRecordRepository.create_record(
                    intent=intent,
                    user=user.user,
                    message=rendered_message,
                    medium=medium
                )
                
                sent_status = NotificationService.send_message(user, medium, rendered_message, record)
                NotificationRecordRepository.mark_record_as_sent(record, sent_status)
        
        NotificationIntentRepository.mark_intent_as_processed(intent)

    @staticmethod
    def render_message(template_str, variables):
        template = Template(template_str)
        context = Context({**variables})
        return template.render(context)

    @staticmethod
    def send_message(user, medium, message, record):
        if medium == 'email':
            # Collect all user emails for bulk sending
            emails = [user.email for user in UserRepository.get_users_by_ids(record.user_ids)]
            return NotificationService.send_email(emails, message)
        elif medium == 'telegram':
            return NotificationService.send_telegram(user.telegram_chat_id, message)
        return False  # If medium is not recognized

    @staticmethod
    def send_email(emails_with_messages, subject="Notification"):
        try:
            # Prepare messages for each recipient in the batch
            messages = [
                (subject, message, settings.DEFAULT_FROM_EMAIL, [email]) 
                for email, message in emails_with_messages
            ]
            
            # Use Django's send_mass_mail function
            result = send_mass_mail(messages, fail_silently=False)
            if not result:
                print("Error sending bulk emails.")
                return False
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

    @staticmethod
    def send_telegram(chat_id, message):
        try:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=payload)
            response.raise_for_status()
            return True  # Indicate success
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False  # Indicate failure
