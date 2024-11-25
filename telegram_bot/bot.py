import nest_asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import asyncio
from .handlers import TelegramBotHandler
from accounts.models import User
from telegram_bot.repositories import TelegramChatDataRepository

# Apply nest_asyncio to allow nested event loops
nest_asyncio.apply()

class TelegramBot:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        return cls._instance
    
    def __init__(self, token: str):
        self.token = token
        self.handler = TelegramBotHandler()
        self.application = Application.builder().token(self.token).build()
        
    async def send_message(self, chat_id: int, message: str) -> None:
        """Send a message to a specific Telegram chat"""
        await self.application.bot.send_message(chat_id, message)
        
    async def start(self):
        """Start the bot"""
        # Create application

        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.handler.start_command))
        # Add message handler for text messages
        self.application.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND, 
                self.handler.message_handler
            )
        )

        # Start the bot
        print("Bot is starting...")
        print(f"Share this link with users: https://web.telegram.org/k/#@Ap32_bot")
        #await self.send_message('6092052374', "Hello")
        await self.application.run_polling()

def run_bot(token: str):
    """Run the bot with the given token"""
    bot = TelegramBot(token)
    loop = asyncio.get_event_loop()
    loop.create_task(bot.start())
    loop.run_forever()

