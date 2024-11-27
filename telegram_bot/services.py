from typing import Optional
from accounts.models import User
from .repositories import TelegramChatDataRepository

class TelegramBotService:
    def __init__(self):
        self.chat_repository = TelegramChatDataRepository()

    async def handle_start_command(self, user_name: str) -> str:
        """Handle the /start command"""
        return (
            f"👋 Hi {user_name}!\n"
            "Welcome to our bot."
        )

    async def handle_existing_start_command(self, user_name: str) -> str:
        """Handle the /start command"""
        return (
            f"👋 Hi {user_name}!\n"
            "Welcome Back."
        )
        
    async def handle_user_message(self, user: User, chat_id: int, message_text: str) -> Optional[str]:
        """Handle incoming user messages"""
        # Log the received message
        print(f"Received message from {chat_id}: {message_text}")

        return None