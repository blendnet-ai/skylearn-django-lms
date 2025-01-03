import logging
from django.conf import settings
from evaluation.event_flow.services.base_rest_service import BaseRestService
from telegram_bot.interfaces import TelegramInterface, TelegramMessage
from telegram_bot.repositories import TelegramChatDataRepository

logger = logging.getLogger(__name__)

class TelegramService(TelegramInterface,BaseRestService):
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.repository = TelegramChatDataRepository
        super().__init__()

    def get_base_headers(self):
        return {}
    
    def get_base_url(self) -> str:
        return self.base_url
    
    async def send_message(self, message: TelegramMessage) -> bool:
        try:
            url = f"{self.base_url}/sendMessage"
            payload = {
                'chat_id': message.chat_id,
                'text': message.text,
                'parse_mode': message.parse_mode
            }
            if message.reply_markup:
                payload['reply_markup'] = message.reply_markup
            response = self._post_request(url=url,data=payload)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {str(e)}")
            return False
