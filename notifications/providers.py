from abc import ABC, abstractmethod
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.utils.html import strip_tags
import requests
from telegram_bot.services.telegram_service import TelegramService

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
        try:
            for data in messages_data:
                print("ok",data)
                user_variables=data.get('variables', {})
                print(user_variables)
                subject = user_variables.get('email_subject','Notification')
                html_content = data['message']
                text_content = strip_tags(html_content)
                from_email = settings.DEFAULT_FROM_EMAIL
                recipient = data['recipient']
                
                email = EmailMultiAlternatives(
                    subject=subject,
                    body=text_content,
                    from_email=from_email,
                    to=[recipient]
                )
                email.attach_alternative(html_content, "text/html")
                email.send(fail_silently=False)
                
            return True
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