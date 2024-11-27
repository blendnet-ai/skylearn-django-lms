from datetime import datetime
import logging

from evaluation.event_flow.helpers.pitch import evaluate_pitch
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from storage_service.azure_storage import AzureStorageService

logger = logging.getLogger(__name__)


class Pitch(EventProcessor):
    def initialize(self):
        azure_obj = AzureStorageService()
        # self.audio_blob_path = self.root_arguments.get("audio_blob_path")
        self.converted_audio_output_path = self.root_arguments.get("converted_audio_blob_path")
        self.storage_container_name = self.root_arguments.get("storage_container_name")
        wav_binary_data = azure_obj.read_blob(self.storage_container_name, self.converted_audio_output_path)
        self.sound_file = "wav_binary_data" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".wav"
        with open(self.sound_file, "wb") as f:
            f.write(wav_binary_data)

    def _execute(self):
        self.initialize()
        pitch_url, plot_name, overstressed_words, understressed_words, remark = evaluate_pitch(self.converted_audio_output_path, self.storage_container_name, self.sound_file)
        return {"pitch_url": pitch_url, "blob_path":plot_name, "observation":remark,"container_name":self.storage_container_name, "overstressed_words": overstressed_words, "understressed_words": understressed_words}