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
    Completeness: str
    Completeness_Reason: str
    Relevance: str
    Relevance_Reason: str
    Logical: str
    Logical_Reason: str
    Overall: str
    Overall_Reason: str


class Coherence(BaseLLMProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_template = ValidPromptTemplates.COHERENCE_PROCESSOR
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
        self.log_info(f"Extracted text - {user_answer}")

        self.context["user_answer"] = user_answer
        self.context["question"] = self.root_arguments["question"]

    def format_response(self, response: dict) -> dict:
        overall_score = response.get("Overall")
        return {"response": response, "score": overall_score}
