from abc import ABC, abstractmethod
from django.template import Template, Context
from django.conf import settings
from django.core.mail import send_mass_mail
import requests

class NotificationProvider(ABC):
    @abstractmethod
    def send_message(self, messages_data):
        """Send messages using the provided message data
        
        Args:
            messages_data (list): List of dictionaries containing:
                - recipient: The recipient ID (email/chat_id)
                - message: The rendered message
                - variables: Additional variables for the message
        """
        pass

class EmailNotificationProvider(NotificationProvider):
    def send_message(self, messages_data, **kwargs):
        subject = kwargs.get('subject', "Notification")
        messages = [
            (subject, data['message'], settings.DEFAULT_FROM_EMAIL, [data['recipient']]) 
            for data in messages_data
        ]
        try:
            result = send_mass_mail(messages, fail_silently=False)
            return bool(result)
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

class TelegramNotificationProvider(NotificationProvider):
    def send_message(self, messages_data, **kwargs):
        try:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            success = True
            
            for data in messages_data:
                payload = {
                    'chat_id': data['recipient'],
                    'text': data['message'],
                    'parse_mode': 'HTML'
                }
                response = requests.post(url, data=payload)
                response.raise_for_status()
                if not response.ok:
                    success = False
            return success
        except Exception as e:
            print(f"Error sending Telegram message: {e}")
            return False