import typing
from enum import Enum
import random
import re

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, date
import logging

from OpenAIService.repositories import ChatHistoryRepository, LLMCommunicationWrapper
from ai_learning.models import PromptTemplates
from evaluation.models import DSAPracticeChatData
from django.db.models import F
from django.db.models import F
logger = logging.getLogger(__name__)

@dataclass
class CompileDurationLog:
    timestamp: int
    duration: float

class PromptTemplateRepository:
    class PromptName(Enum):
        DSA_PRACTICE = "dsa_practice_prompt"

    @staticmethod
    def get_prompt_object(name: PromptName):
        prompt_template = PromptTemplates.objects.get(name=name)
        return prompt_template

    @staticmethod
    def sanitize_prompt(prompt):
        # Replace control characters like newlines and tabs with escaped versions
        sanitized = re.sub(r"([\n\t\r])", r"\\\1", prompt)
        return sanitized


class DSAPracticeChatDataRepository:
    @staticmethod
    def get_chat_history_for_reporting(chat_history):
        """
        Process the chat history to filter out system-generated messages and
        count the number of user messages.
        """
        if chat_history is None:
            return [], 0
        filtered_history = [chat for chat in chat_history if chat.get('role') in ['user', 'assistant'] and not chat.get('system_generated', False)]
        user_count = sum(1 for chat in filtered_history if chat.get('role') == 'user' and not chat.get('system_generated', False))

        return filtered_history, user_count

    @staticmethod
    def get_or_create(user_id, question_id, assessment_attempt_id):
        user_data, created = DSAPracticeChatData.objects.get_or_create(
            user_id=user_id,
            question_id=question_id,
            assessment_attempt_id=assessment_attempt_id,
        )
        return user_data, created

    @staticmethod
    def add_chat_history_id(dsa_practice_data: DSAPracticeChatData, chat_history_id:int):
        if dsa_practice_data.chat_history_obj is None:
            dsa_practice_data.chat_history_obj_id = chat_history_id
            dsa_practice_data.save()
        else:
            logger.error(f"Chat history object already exists. DSAPracticeChatData id = {dsa_practice_data.id}")


    @staticmethod
    def save_run_log(*, user_id:int,question_id:int,assessment_attempt_id:int, compile_duration_log:CompileDurationLog, submit=False):
        #obj = DSAPracticeChatData.objects.get(assessment_attempt_id=assessment_attempt_id)
        obj,_ = DSAPracticeChatDataRepository.get_or_create(user_id,question_id,assessment_attempt_id)
        if not submit:
            obj.compile_duration_logs.append(asdict(compile_duration_log))
            obj.save()
        else:
            obj.submit_compile_log = asdict(compile_duration_log)
            obj.save()

    def get(user_id, question_id, assessment_attempt_id):
        try:
            user_data = DSAPracticeChatData.objects.get(
                user_id=user_id,
                question__id=question_id,
                assessment_attempt__assessment_id=assessment_attempt_id,
            )
            return user_data
        except DSAPracticeChatData.DoesNotExist:
            return None

    @staticmethod
    def fetch_chat_sessions(user_id, assessment_attempt_ids):
        # Fetch chat sessions based on user_id and assessment_attempt_ids
        chat_sessions = DSAPracticeChatData.objects.filter(
            user_id=user_id,
            assessment_attempt_id__in=assessment_attempt_ids,
            chat_history_obj_id__isnull=False
        ).annotate(
            llm_chat_history=F('chat_history_obj__chat_history')
        )


        chat_sessions_list = list(chat_sessions)
        for session in chat_sessions_list:
            session.llm_chat_history, session.llm_chat_count = DSAPracticeChatDataRepository.get_chat_history_for_reporting(session.llm_chat_history)

        return chat_sessions_list



    @staticmethod
    def _generate_12_digit_random_id():
        min_num = 10**11
        max_num = (10**12) - 1
        return random.randint(min_num, max_num)


    @staticmethod
    def add_proactive_bot_msg_old(user_data: DSAPracticeChatData, msg: str, delay: int):
        conversational_history = user_data.chat_history
        bot_message = {
            "message": msg,


            "type": "bot",
            "timestamp": int(datetime.now().timestamp()),
            "open_chat_window": True,
            "is_proactive_message": True,
            "delay": delay,
        }
        conversational_history.append(bot_message)
        user_data.chat_history = conversational_history
        user_data.save()
        return bot_message

    @staticmethod
    def add_proactive_bot_msg(user_data: DSAPracticeChatData, msg: str):
        bot_message = {
            "content": msg,
            "role": "assistant",
            "system_generated": True,
        }
        chat_repo = ChatHistoryRepository(chat_history_id=user_data.chat_history_obj.id)
        chat_repo.add_msgs_to_chat_history([bot_message],commit_to_db=True)
        return bot_message

    @staticmethod
    def update_chat_history(*, user_data:DSAPracticeChatData , user_msg:str, bot_msg:str, user_msg_timestamp:int|float, bot_msg_timestamp:int|float, message_generation_time:int|float,code:str):
        conversational_history = user_data.chat_history

        user_message = {
            "message": user_msg,
            "id": DSAPracticeChatDataRepository._generate_12_digit_random_id(),
            "type": "user",
            "timestamp": user_msg_timestamp
        }

        bot_message = {
            "message": bot_msg,

            "code":code,
            "id": DSAPracticeChatDataRepository._generate_12_digit_random_id(),
            "type": "bot",
            "timestamp": bot_msg_timestamp,
            "message_generation_time": message_generation_time
        }

        conversational_history.append(user_message)
        conversational_history.append(bot_message)

        user_data.chat_history = conversational_history
        user_data.chat_count += 1

        user_data.save()
    
    @staticmethod
    def get_chat_sessions_for_assessments(assessment_attempt_ids):
        chat_sessions = DSAPracticeChatData.objects.filter(
            assessment_attempt_id__in=assessment_attempt_ids
        ).annotate(
            llm_chat_history=F('chat_history_obj__chat_history')
        )

        chat_sessions_list = list(chat_sessions)

        for session in chat_sessions_list:
            session.llm_chat_history, session.llm_chat_count = DSAPracticeChatDataRepository.get_chat_history_for_reporting(session.llm_chat_history)

        return chat_sessions_list
    
    @staticmethod
    def get_chat_data_by_assessment_id(assessment_id):
        obj = DSAPracticeChatData.objects.filter(assessment_attempt__assessment_id=assessment_id).annotate(
            llm_chat_history=F('chat_history_obj__chat_history')
        ).first()

        if obj:
            return obj.llm_chat_history
        else:
            return []

    @staticmethod
    def get_chat_session_history(user_id, question_id, assessment_attempt_id):
        try:
            chat_session = DSAPracticeChatData.objects.filter(
                user_id=user_id,
                question__id=question_id,
                assessment_attempt__assessment_id=assessment_attempt_id
            ).annotate(
                llm_chat_history=F('chat_history_obj__chat_history')
            ).get()

            llm_chat_history, _ = DSAPracticeChatDataRepository.get_chat_history_for_reporting(chat_session.llm_chat_history)
            return llm_chat_history
        except DSAPracticeChatData.DoesNotExist:
            return None
