import logging
import requests
import json

from evaluation.event_flow.helpers.coherence import evaluate_coherence
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.processors.expections import ProcessorException
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class Coherence(EventProcessor):

    def get_fallback_result(self):
        return self._fallback_result

    def initialize_v2(self):
        self.user_answer = self.root_arguments.get("text")
        if self.user_answer is None:
            self.transcript_url = self.inputs["SpeechToText"]["output_transcript_url"]
            response = requests.get(self.transcript_url, allow_redirects=True)
            # if response.status_code!=200:
            #     raise Exception(f"Error in reading transcript. Response code = {response.status_code}. Response - {response.content}")
            self.user_answer = str(response.content)
        
        self.log_info(f"Extracted text - {self.user_answer}")
        self.question = self.root_arguments["question"]

    def initialize(self):
        self.user_answer = self.root_arguments.get("text")
        if self.user_answer is None:
            self.transcript_url = self.inputs["SpeechToText"]["output_transcript_url"]
            response = requests.get(self.transcript_url, allow_redirects=True)
            if response.status_code!=200:
                raise Exception(f"Error in reading transcript. Response code = {response.status_code}. Response - {response.content}")
            self.user_answer = response.content.decode('utf-8')
        self.log_info(f"Extracted text - {self.user_answer}")
        self.question = self.root_arguments["question"]

    def _execute(self):
        self.initialize()
        llm_object = OpenAIService()
        response = evaluate_coherence(self.question, self.user_answer, llm_object)
        try:
            response_json = json.loads(response)
        except Exception as e:
            self.log_info(f"Got exception while decoding LLM response -{e} .LLM RESPONSE was \n{response}.\n")
            self._fallback_result = {"response": {"Completeness" : "",
                                "Completeness_Reason" : "",
                                "Relevance" : "",
                                "Relevance_Reason" : "",
                                "Logical":"",
                                "Logical_Reason":"",
                                "Overall" : "Good",
                                "Overall_Reason" : ""},
                                "score": 0}
            raise ProcessorException(message="Coherence error while parsing llm response", original_error=e,
                                     extra_info={})

        overall_score = response_json.get("Overall")
        return {"response": response_json, "score":overall_score}