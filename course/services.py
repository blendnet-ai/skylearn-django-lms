import requests
from django.core.mail import EmailMessage
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class MessageService:
    @staticmethod
    def send_telegram_message(chat_id, message):
        """Send message via Telegram"""
        try:
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            response = requests.post(url, data=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Telegram message failed for chat_id {chat_id}: {str(e)}")
            return False

    @staticmethod
    def send_email_message(email, subject, message):
        """Send message via email"""
        try:
            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email]
            )
            email.send()
            return True
        except Exception as e:
            logger.error(f"Email failed for {email}: {str(e)}")
            return False 