from custom_auth.repositories import UserProfileRepository
from telegram import Update
from telegram.ext import ContextTypes
from accounts.models import User
from .services import TelegramBotService
from .repositories import TelegramChatDataRepository
from custom_auth.models import UserProfile

class TelegramBotHandler:
    def __init__(self):
        self.service = TelegramBotService()
        self.test_user = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start command"""
        chat_id = update.effective_chat.id
        
        # Check if chat_id already exists
        self.test_user,existing_chat_id = await TelegramChatDataRepository.get_entry_by_chat_id(chat_id)
        
        if self.test_user and str(chat_id)==str(existing_chat_id):
            welcome_message = await self.service.handle_start_command(self.test_user.first_name)
            await update.message.reply_text(welcome_message)
        else:
            try:
                # Get OTP from context args
                if not context.args:
                    await update.message.reply_text("Please use valid link sent through email")
                    return
                    
                otp = context.args[0]
                print(otp)
                # Try to find user profile with matching OTP
                user_profile,self.test_user = await TelegramChatDataRepository.get_user_profile(otp=otp)

                # Handle successful verification
                welcome_message = await self.service.handle_start_command(self.test_user.first_name)
                stored_chat_id = await TelegramChatDataRepository.get_telegram_chat_id(self.test_user)

                if stored_chat_id is None or str(stored_chat_id) != str(chat_id):
                    await TelegramChatDataRepository.save_telegram_chat_id(self.test_user, chat_id)
                    print(self.test_user)
                    await UserProfileRepository.set_telegram_onboarding_complete(self.test_user)
                    print("saved chat id")

                await update.message.reply_text(welcome_message)

            except UserProfile.DoesNotExist:
                await update.message.reply_text("Invalid OTP. Please try again.")
            except IndexError:
                await update.message.reply_text("Please use valid link send through email.")

    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for incoming text messages"""
        chat_id = update.effective_chat.id
        message_text = update.message.text

        # Only handle regular messages if user is verified
        if self.test_user:
            response = await self.service.handle_user_message(
                self.test_user,
                chat_id,
                message_text
            )
            if response:
                await update.message.reply_text(response)
        else:
            await update.message.reply_text("Please verify using /start command first")