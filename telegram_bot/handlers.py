from telegram import Update
from telegram.ext import ContextTypes
from .services.telegram_service import TelegramService
from custom_auth.models import UserProfile
from custom_auth.repositories import UserProfileRepository
from telegram_bot.interfaces import TelegramMessage
from telegram_bot.repositories import TelegramChatDataRepository
from notifications.repositories import UserRepository

class TelegramCommandHandler:
    def __init__(self):
        self.telegram_service = TelegramService()

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        chat_id = update.effective_chat.id
        if not context.args:
            await update.message.reply_text("Please use valid link from platform")
            return

        try:
            # Get OTP from context args
            otp = context.args[0]
            
            # Try to find user profile with matching OTP
            user_profile, user_id = await TelegramChatDataRepository.get_user_profile(otp=otp)
            
            # Check if this user already has a different chat_id connected
            existing_chat_id = await TelegramChatDataRepository.get_telegram_chat_id(user_id)
            if existing_chat_id and str(existing_chat_id) != str(chat_id):
                await update.message.reply_text(
                    "This account is already connected to a different Telegram account. "
                    "Please disconnect the existing Telegram account first or use the same Telegram account."
                )
                return
            
            # Check if this chat_id is already connected to a different user
            other_user, existing_chat_id, other_email = await TelegramChatDataRepository.get_entry_by_chat_id(chat_id)
            if other_user and other_user.id != user_id:
                await update.message.reply_text(
                    "This Telegram account is already connected to another user "
                    f"({other_email}). Please use a different Telegram account."
                )
                return

            # If we get here, either:
            # 1. This is a new connection
            # 2. This is the same user reconnecting with the same Telegram account
            welcome_message = TelegramMessage(
                chat_id=str(chat_id),
                text=f"👋 Hi User!\nWelcome to our bot."
            )
            
            # Save/update the chat_id
            await TelegramChatDataRepository.save_telegram_chat_id(user_id, chat_id)
            await UserRepository.add_user_info(user_id.id, user_id.email, chat_id)
            await UserProfileRepository.set_telegram_onboarding_complete(user_id)
            await self.telegram_service.send_message(welcome_message)

        except UserProfile.DoesNotExist:
            await update.message.reply_text("Invalid OTP. Please try again.")
