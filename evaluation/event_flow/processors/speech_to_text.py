import json
import subprocess
from datetime import datetime, timedelta
import logging
import random
import string
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.processors.expections import CriticalProcessorException
from evaluation.event_flow.services.whisper_timestamped_service import WhisperTimestampService,DeepgramWhisperService
from storage_service.azure_storage import AzureStorageService

logger = logging.getLogger(__name__)

WORDS_THRESHOLD = 10

class SpeechToText(EventProcessor):
    """
    Testing code
    inputs={}
    dt_append=datetime.now().strftime('%d|%m-%H:%M')
    root_args={"audio_blob_path":"22034211060_Gavit Nitin.wav",
                "converted_audio_blob_path":"sanchit_tst/{dt_append}/converted_audio.wav"
               "base_storage_path":f"sanchit_tst/{dt_append}",
               "storage_container_name":"tst",
               "evaluation_id":'95dc32a0-20fe-4874-a482-513d0dad3daa',
               "question":"Introduce yourself and your interests?"}
    stt=SpeechToText(eventflow_id="temp_id",inputs=inputs,root_arguments=root_args)
    stt._execute()
    //Sample output
    {'success': None,
        'output_transcript_url': 'https://stspeechaistage.blob.core.windows.net/tst/sanchit_tst/12|10-05:27/SpeechToText/transcript.txt?se=2023-10-12T15%3A27%3A36Z&sp=rw&sv=2023-08-03&sr=b&sig=1%2BLgQSZWOixIpm0jIW2lfA%2Blr3eZTrcofsQyuyLJVOA%3D',
        'full_output_url': 'https://stspeechaistage.blob.core.windows.net/tst/sanchit_tst/12|10-05:27/SpeechToText/full_output.json?se=2023-10-12T15%3A27%3A36Z&sp=rw&sv=2023-08-03&sr=b&sig=4qY5PN%2BAV%2B/t7p9/qHxA7wQekD6P4ZjFtcIjVySzQNA%3D',
        'converted_audio_output_url': 'https://stspeechaistage.blob.core.windows.net/tst/sanchit_tst/12|10-05:27/SpeechToText/converted_audio.json?se=2023-10-12T15%3A27%3A36Z&sp=rw&sv=2023-08-03&sr=b&sig=V8KXfXjHWADTQtLiEzUJ5cWdjAX8JgiAv/%2BWKuW7dZI%3D'}
    """
    def get_sass_url(self, blob_path, allow_write=False, allow_read=False):
        expiry_time = datetime.now() + timedelta(hours=10)
        return self.azure_storage_service.generate_blob_access_url(
            container_name=self.storage_container_name,
            blob_name=blob_path,
            expiry_time=expiry_time, allow_write=allow_write,
            allow_read=allow_read)

    @staticmethod
    def get_random_string(prefix="", suffix="", length: int = 10):
        return prefix + ''.join(random.choices(string.ascii_lowercase + string.digits, k=length)) + suffix

    def initialize(self):
        self.base_path = self.root_arguments.get("base_storage_path")
        self.audio_blob_path = self.root_arguments.get("audio_blob_path")
        self.question = self.root_arguments.get("question")
        self.question_attempt_id = self.root_arguments.get("question_attempt_id")
        self.converted_audio_output_path = self.root_arguments.get("converted_audio_blob_path")
        self.storage_container_name = self.root_arguments.get("storage_container_name")
        self.output_transcript_path = f"{self.base_path}/{self.__class__.__name__}/{self.question_attempt_id}/transcript.txt"
        self.full_output_path = f"{self.base_path}/{self.__class__.__name__}/{self.question_attempt_id}/full_output.json"

        self.azure_storage_service = AzureStorageService()
        # making more than 5 hours to handle timezone thing for now. TODO - change this to an appropriate time

        self.audio_url = self.get_sass_url(self.audio_blob_path,allow_read=True)
        self.output_transcript_url = self.get_sass_url(self.output_transcript_path,allow_write=True,allow_read=True)
        self.full_output_url = self.get_sass_url(self.full_output_path,allow_write=True,allow_read=True)
        self.converted_audio_sass_url = self.get_sass_url(self.converted_audio_output_path,allow_write=True,allow_read=True)
        self.speech_to_text_service = WhisperTimestampService()
        self.deepgram_service = DeepgramWhisperService()

    def convert_audio(self, *, audio_path, converted_audio_path):
        result = subprocess.run(
            ['ffmpeg', '-i', audio_path, '-acodec', 'pcm_s16le', '-ac', '1', '-ar', '48000', converted_audio_path],
            stdout=subprocess.PIPE)
        if result.returncode != 0:
            output = result.stdout.decode()
            raise ValueError(f"Got error while converting audio. FFMPEG output =  {output}")

    def convert_and_upload_audio(self):
        temp_initial_audio_path = self.get_random_string("initial_audio_",".wav")
        temp_converted_audio_path = self.get_random_string("initial_converted_audio_",".wav")
        self.azure_storage_service.download_blob(container_name=self.storage_container_name,
                                                 blob_name=self.audio_blob_path, file_path=temp_initial_audio_path)
        self.convert_audio(audio_path=temp_initial_audio_path, converted_audio_path=temp_converted_audio_path)
        converted_audio_bytes = open(temp_converted_audio_path, "rb").read()
        self.azure_storage_service.upload_blob(container_name=self.storage_container_name,
                                               blob_name=self.converted_audio_output_path,
                                               content=converted_audio_bytes)

    def _execute(self):
        self.initialize()
        self.convert_and_upload_audio()
        # result = self.speech_to_text_service.speech_to_text(audio_url=self.audio_url,
        #                                                     transcript_url=self.output_transcript_url,
        #                                                     full_output_url=self.full_output_url,
        #                                                     converted_audio_output_url=self.converted_audio_output_url)
        try:
            # result = self.deepgram_service.speech_to_text(audio_url=self.converted_audio_sass_url)
            result = self.speech_to_text_service.speech_to_text(audio_url=self.converted_audio_sass_url)
        except Exception as ex:
            msg = "Error while getting transcript from speech to text service"
            raise CriticalProcessorException(message=msg, original_error=ex, extra_info={})
        
        timed_words = [{"word":timed_word.word,
                        "start":timed_word.start,
                        "end":timed_word.end} for timed_word in result.timed_words]
        full_output = {"timed_words":timed_words, "transcript":result.transcript}

        if len(timed_words) < WORDS_THRESHOLD:
            msg = f"SpeechToText got less than {WORDS_THRESHOLD} words in transcription"
            ex = Exception(msg)
            #Sanchit Todo -  this way of raising error is resulting in neither msg nor stacktrace being stored in processor logs. FIX THIS.
            raise CriticalProcessorException(message=msg, original_error=ex, extra_info={})

        self.azure_storage_service.upload_blob(self.storage_container_name, self.output_transcript_path,
                                               result.transcript.encode("utf-8"))
        self.azure_storage_service.upload_blob(self.storage_container_name, self.full_output_path,
                                               json.dumps(full_output).encode("utf-8"))


        return {
                "output_transcript_url":self.output_transcript_url,
                "full_output_url":self.full_output_url,
                "converted_audio_output_url":self.converted_audio_sass_url
                }
        
        
