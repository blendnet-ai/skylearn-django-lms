import logging
import requests

from openai import BaseModel
from textblob import TextBlob
from data_repo.models import QuestionBank
from common.utilities import round_to_pt5
from OpenAIService.repositories import (
    ValidPromptTemplates,
)
from evaluation.event_flow.helpers.sentiment import evaluate_sentiment
from evaluation.event_flow.processors.base_llm_processor import BaseLLMProcessor

logger = logging.getLogger(__name__)


class Response(BaseModel):
    class Error(BaseModel):
        incorrect: str
        correct: str
        grammatical_error: str
        reason: str

    errors: list[Error]


class BaseGrammar(BaseLLMProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_template = ValidPromptTemplates.GRAMMAR_PROCESSOR
        self.response_format_class = Response
        self.question_type = None

    def initialize(self):
        super().initialize()
        self.user_answer = self.root_arguments.get("text")
        if self.user_answer is None:
            self.transcript_url = self.inputs["SpeechToText"]["output_transcript_url"]
            response = requests.get(self.transcript_url, allow_redirects=True)
            if response.status_code != 200:
                raise Exception(
                    f"Error in reading transcript. Response code = {response.status_code}. Response - {response.content}"
                )
            self.user_answer = response.content.decode("utf-8")

        self.context["user_answer"] = self.user_answer

    def calculate_score(score_ranges, param, question_type):
        for length, score in score_ranges[question_type].items():
            if param < length:
                return score

    def format_response(self, response: dict) -> dict:
        errors = response.get("errors")

        error_count = {}
        final_error_response = []
        for item in errors:
            if (item.get("grammatical_error")).lower() != "no error" and item.get(
                "grammatical_error"
            ):
                final_error_response.append(item)
                error_count[item.get("grammatical_error")] = (
                    error_count.get(item.get("grammatical_error"), 0) + 1
                )

        total_errors = len(final_error_response)
        blob = TextBlob(self.user_answer)
        total_words = len(blob.words)
        sentences = blob.sentences
        average_sentence_length = (
            total_words / len(sentences) if len(sentences) != 0 else 0
        )
        error_density = (total_errors / total_words) * 100

        sentence_length_score_ranges = {
            QuestionBank.QuestionType.IELTS: {
                10: 2,
                15: 4.5,
                20: 6.5,
                float("inf"): 8.5,
            },
            QuestionBank.QuestionType.INTERVIEW_PREP: {
                10: 4,
                15: 6,
                20: 8,
                float("inf"): 10,
            },
        }
        sentence_length_score = BaseGrammar.calculate_score(
            sentence_length_score_ranges, average_sentence_length, self.question_type
        )

        error_density_score_ranges = {
            QuestionBank.QuestionType.IELTS: {1: 9, 5: 8, 10: 6.5, float("inf"): 3},
            QuestionBank.QuestionType.INTERVIEW_PREP: {
                1: 10,
                5: 8,
                10: 4,
                float("inf"): 2,
            },
        }
        error_density_score = BaseGrammar.calculate_score(
            error_density_score_ranges, error_density, self.question_type
        )

        score = 0.7 * sentence_length_score + 0.3 * error_density_score

        return {
            "score": round_to_pt5(score),
            "sentence_correction": errors,
            "common_mistakes": error_count,
            "incorrect_speech_percentage": error_density_score,
        }
