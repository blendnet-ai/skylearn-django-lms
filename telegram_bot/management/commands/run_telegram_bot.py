from django.core.management.base import BaseCommand
from telegram_bot.telegram_bot import TelegramBot
import asyncio
import nest_asyncio

class Command(BaseCommand):
    help = 'Starts the Telegram bot'

    def handle(self, *args, **options):
        self.stdout.write('Starting Telegram bot...')
        # Apply nest_asyncio to allow nested event loops
        nest_asyncio.apply()
        
        bot = TelegramBot()
        # Create new event loop and run the bot
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(bot.run_bot())
        finally:
            loop.close()