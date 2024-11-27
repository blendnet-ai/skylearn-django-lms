import logging
import requests

from evaluation.event_flow.helpers.fillerWords import evaluate_fillerWords
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.processors.expections import ProcessorEvaluationException, ProcessorException
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class FillerWords(EventProcessor):

    def get_fallback_result(self):
        return self._fallback_result
    
    def initialize(self):
        self.text = self.root_arguments.get("text")
        if self.text is None:
            self.transcript_url = self.inputs["SpeechToText"]["output_transcript_url"]
            response = requests.get(self.transcript_url, allow_redirects=True)
            if response.status_code != 200:
                raise Exception(
                    f"Error in reading transcript. Response code = {response.status_code}. Response - {response.content}")
            self.text = response.content.decode('utf-8')

    def _execute(self):
        self.initialize()
        llm_object = OpenAIService()
        try:
            user_input, filler_word_count, response, fillerwords = evaluate_fillerWords(self.text, llm_object)
        except ProcessorEvaluationException as e:
            self._fallback_result = {"score": 0, "user_input": self.text,
                                    "response": "", "count": 0, "fillerwords": []}
            raise ProcessorException(message="Filler words evaluation error", original_error=e,
                                     extra_info={})

        return {"user_input": user_input,
                "response":response, "count": filler_word_count, "fillerwords": fillerwords}