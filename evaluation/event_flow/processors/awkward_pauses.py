import logging
import requests
import json

from evaluation.event_flow.helpers.awkwardPauses import evaluate_awkwardPauses
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.processors.storagemixin import ProcessorStorageMixin

logger = logging.getLogger(__name__)


class AwkwardPauses(EventProcessor, ProcessorStorageMixin):

    def set_vars_from_full_output_json(self):
        self.full_output_json_url = self.inputs["SpeechToText"]["full_output_url"]
        response = self.download_file_get_content(url=self.full_output_json_url)
        full_output_json = json.loads(response.content.decode('utf-8'))
        self.timed_words = full_output_json["timed_words"]
        self.transcript = full_output_json["transcript"]

    def initialize(self):
        self.threshold = 1.5
        self.set_vars_from_full_output_json()

    def _execute(self):
        self.initialize()
        count, response = evaluate_awkwardPauses(timed_words=self.timed_words,
                                                                awkward_pause_threshold=self.threshold)
        total_word_count = len(self.transcript.strip().split(" "))
        return {"original_text": self.transcript, "count": count,
                "total_words_count": total_word_count, "response": response}