import json
import random
from string import Template
from channels.generic.websocket import WebsocketConsumer
from datetime import datetime
from ai_learning.models import PromptTemplates
from ai_learning.repositories import (
    DSAPracticeChatDataRepository,
    PromptTemplateRepository,
)
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService
from custom_auth.authentication import FirebaseAuthentication
from evaluation.models import DSAPracticeChatData, Question

import logging

from evaluation.repositories import QuestionRepository,AssessmentAttemptRepository
from evaluation.seriailzers import DSABotRequestSerializer
from evaluation.usecases import DSABotWebsocketConsumerUseCase

logger = logging.getLogger(__name__)


class BotWebsocketConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, _):
        if hasattr(self, 'assessment_id') and self.assessment_id:
            AssessmentAttemptRepository.update_assessment_time(assessment_id=self.assessment_id,updated_timestamp=datetime.utcnow())
            logging.info("Assessment data updated successfully")
        #this event of disconnect occurs when socket disconnects so no need to close it manually
        #socket close is typically used when we need to disconnect websocket connection forcefully.


class DSABotWebsocketConsumer(BotWebsocketConsumer):
    def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('for_init',False):
            self.assessment_id=data.get('assessment_id',None)
        else:
            serializer = DSABotRequestSerializer(data=data)

            if serializer.is_valid():
                user_input = serializer.validated_data["message"]
                question_id = serializer.validated_data["question_id"]
                assessment_attempt_id = serializer.validated_data["assessment_id"]
                token = serializer.validated_data["token"]
                code = serializer.validated_data["code"]
                language = serializer.validated_data["language"]
                run_result = serializer.validated_data["run_result"]

                user, _ = FirebaseAuthentication.authenticate_token(token)
                user_id = user.id

                response = DSABotWebsocketConsumerUseCase.handle_request_2(
                    user_input,
                    user_id,
                    question_id,
                    assessment_attempt_id,
                    code,
                    language,
                    run_result
                )
            else:
                response = serializer.errors

            self.send(text_data=json.dumps({"message": response}))