import logging
import requests
import json

from evaluation.event_flow.helpers.pace import evaluate_pace
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.processors.storagemixin import ProcessorStorageMixin

logger = logging.getLogger(__name__)


class Pace(EventProcessor,ProcessorStorageMixin):

    def set_vars_from_full_output_json(self):
        self.full_output_json_url = self.inputs["SpeechToText"]["full_output_url"]
        response = self.download_file_get_content(url=self.full_output_json_url)
        full_output_json = json.loads(response.content.decode('utf-8'))
        self.timed_words = full_output_json["timed_words"]
        self.transcript = full_output_json["transcript"]

    def initialize(self):
        self.window_duration = 1
        self.set_vars_from_full_output_json()
        self.audio_blob_path = self.root_arguments.get("audio_blob_path")
        self.storage_container_name = self.root_arguments.get("storage_container_name")

    def _execute(self):
        self.initialize()
        plot_url, score = evaluate_pace(audio_blob_path=self.audio_blob_path,
                                        storage_container_name=self.storage_container_name,
                                        timed_words=self.timed_words,
                                        window_duration=self.window_duration,
                                        full_transcript=self.transcript)
        return {"plot_url":plot_url, "score":score}