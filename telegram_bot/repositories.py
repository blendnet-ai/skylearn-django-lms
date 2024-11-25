import stat

from custom_auth.repositories import UserProfileRepository
from .models import chats_data
from custom_auth.models import UserProfile
from channels.db import database_sync_to_async

class TelegramChatDataRepository:
    @staticmethod
    def get_telegram_chat_id_sync(user):
        try:
            return chats_data.objects.get(user=user).telegram_chat_id
        except chats_data.DoesNotExist:
            return None
        
    @staticmethod
    @database_sync_to_async
    def get_telegram_chat_id(user):
        try:
            return chats_data.objects.get(user=user).telegram_chat_id
        except chats_data.DoesNotExist:
            return None
    
    @staticmethod 
    @database_sync_to_async
    def save_telegram_chat_id(user, chat_id):
        chat_data, created = chats_data.objects.get_or_create(user=user)
        chat_data.telegram_chat_id = chat_id
        chat_data.save()
        return chat_data
    
    @staticmethod
    @database_sync_to_async
    def get_user_profile(otp):
        return UserProfile.objects.get(otp=otp),UserProfile.objects.get(otp=otp).user_id
    
    @staticmethod
    @database_sync_to_async
    def get_entry_by_chat_id(chat_id: str):
        try:
            telegram_data = chats_data.objects.get(telegram_chat_id=chat_id)
            return telegram_data.user,telegram_data.telegram_chat_id
        except chats_data.DoesNotExist:
            return None ,None