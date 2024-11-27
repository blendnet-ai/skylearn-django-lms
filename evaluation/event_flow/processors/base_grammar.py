import logging
import requests
from common.utilities import round_to_pt5
from evaluation.event_flow.helpers.grammar import evaluate_grammar
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.processors.expections import ProcessorException
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class BaseGrammar(EventProcessor):

    def get_fallback_result(self):
        return self._fallback_result

    def initialize(self):
        self.text = self.root_arguments.get("text")
        if self.text is None:
            self.transcript_url = self.inputs["SpeechToText"]["output_transcript_url"]
            response = requests.get(self.transcript_url, allow_redirects=True)
            if response.status_code != 200:
                raise Exception(
                    f"Error in reading transcript. Response code = {response.status_code}. Response - {response.content}"
                )
            self.text = response.content.decode("utf-8")

    def evaluate_with_specific_question_type(self, text, llm_object):
        raise NotImplementedError

    def _execute(self):
        self.initialize()
        llm_object = OpenAIService()
        try:
            score, errors, error_count, incorrect_speech_percentage = self.evaluate_with_specific_question_type(
                self.text, llm_object
            )
            self.log_info(f"Error count - {error_count}, Errors - {errors}")
        except Exception as e:
            self.log_error(f"Grammar event processor, malformed llm response e: {e}")
            self._fallback_result = {
                "score": 0,
                "sentence_correction": [],
                "common_mistakes": {},
                "incorrect_speech_percentage": 0,
            }
            raise ProcessorException(
                message="Grammar evaluation error, while getting reponse from llm",
                original_error=e,
                extra_info={},
            )

        return {
            "score": round_to_pt5(score),
            "sentence_correction": errors,
            "common_mistakes": error_count,
            "incorrect_speech_percentage": incorrect_speech_percentage,
        }
