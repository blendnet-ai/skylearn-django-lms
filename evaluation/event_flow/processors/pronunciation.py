import requests
import logging

from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.processors.expections import ProcessorException
from django.conf import settings

logger = logging.getLogger(__name__)


class Pronunciation(EventProcessor):

    def get_fallback_result(self):
        return self._fallback_result

    def initialize(self):
        self.transcript_url = self.inputs["SpeechToText"]["output_transcript_url"]
        self.converted_audio_output_path = self.root_arguments.get("converted_audio_blob_path")
        self.storage_container_name = self.root_arguments.get("storage_container_name")

    def _execute(self):
        # self.initialize()
        # url = f"{settings.PRONUNCIATION_SERVICE_ENDPOINT}/pronunciation"
        # headers = {
        #     'pronunciation_token': settings.PRONUNCIATION_SERVICE_AUTH_TOKEN
        # }
        # query_params = {
        #     'transcript_url': self.transcript_url,
        #     'audio_blob_path': self.converted_audio_output_path,
        #     'storage_container_name': self.storage_container_name,
        # }
        try:
        #     response = requests.get(url, headers=headers, params=query_params)
        #     if response.status_code!=200:
        #         raise Exception(f"Error in evaluating pronunciation. Response code = {response.status_code}. Response - {response.content}")
        #     percentage_mispronounced = response.json()["percentage_mispronounced"]
        #     pronunciation_score = response.json()["score"]
        #     mispronounced_words = response.json()["mispronounced_words"]
        #    fluency_score = response.json()["fluency_score"]
        #    return {"percentage_mispronounced": percentage_mispronounced, "fluency_score":fluency_score, "score": pronunciation_score, "words_test": mispronounced_words}
            return {"percentage_mispronounced": 5, "fluency_score":80, "score": 80, "words_test": 80}
        except Exception as e:
            self.log_error(f"Error in evaluating pronunciation - {e}")
            self._fallback_result = {"percentage_mispronounced": 0, "fluency_score":0, "score": 0, "words_test": []}
            raise ProcessorException(message="Pronunciation evaluation error", original_error=e,
                                     extra_info={})
