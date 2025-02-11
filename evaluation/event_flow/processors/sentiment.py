import logging
import requests

from openai import BaseModel

from OpenAIService.repositories import (
    ValidPromptTemplates,
)
from evaluation.event_flow.helpers.sentiment import evaluate_sentiment
from evaluation.event_flow.processors.base_llm_processor import BaseLLMProcessor

logger = logging.getLogger(__name__)


class Response(BaseModel):
    feedback: str
    confidence_rating: str  # HIGH/MODERATE/LOW


class Sentiment(BaseLLMProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_template = ValidPromptTemplates.SENTIMENT_PROCESSOR
        self.response_format_class = Response

    def initialize(self):
        super().initialize()
        user_answer = self.root_arguments.get("text")
        if user_answer is None:
            self.transcript_url = self.inputs["SpeechToText"]["output_transcript_url"]
            response = requests.get(self.transcript_url, allow_redirects=True)
            if response.status_code != 200:
                raise Exception(
                    f"Error in reading transcript. Response code = {response.status_code}. Response - {response.content}"
                )
            user_answer = response.content.decode("utf-8")

        self.sentiment_response = evaluate_sentiment(text=user_answer)
        logger.info(f"Sentiment response: {self.sentiment_response}")
        self.context["user_answer"] = user_answer
        self.context["sentiment_rating"] = self.sentiment_response.sentiment_rating

    def format_response(self, response: dict) -> dict:
        return {
            "sentiment": self.sentiment_response.sentiment_rating,
            "overall_remark": response.get("feedback"),
            "confidence": response.get("confidence_rating"),
        }
