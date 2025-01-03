from telegram.ext import Application, CommandHandler, MessageHandler, filters
from django.conf import settings
from .handlers import TelegramCommandHandler

class TelegramBot:
    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.command_handler = TelegramCommandHandler()
        self.application = Application.builder().token(self.token).build()
        
    async def setup(self):
       self.application.add_handler(
           CommandHandler("start", self.command_handler.start_command)
       )
       
    async def run_bot(self):
       """Run the bot"""
       await self.setup()
       await self.application.run_polling()