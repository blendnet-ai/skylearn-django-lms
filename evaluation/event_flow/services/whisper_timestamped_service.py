import dataclasses
import typing
from django.conf import settings
from .base_rest_service import BaseRestService
import logging
from deepgram import Deepgram

logger = logging.getLogger(__name__)



class WhisperTimestampService(BaseRestService):
    # todo - move settings to settings.py
    TIMEOUT = 100  # settings.WHISPER_TIMESTAMP_READ_TIMEOUT
    CONNECTION_TIMEOUT = 100  # settings.WHISPER_TIMESTAMP_CONNECTION_TIMEOUT

    def __init__(self, **kwargs):
        self.secret_token = settings.WHISPER_TIMESTAMP_SERVICE_AUTH_TOKEN
        super().__init__(**kwargs)

    def get_base_headers(self):
        return {"token": self.secret_token}

    def get_base_url(self) -> str:
        return settings.WHISPER_TIMESTAMP_SERVICE_ENDPOINT

    def speech_to_text_old(self, *, audio_url: str, transcript_url: str, full_output_url: str,
                       converted_audio_output_url: str):
        data = {"audio_url": audio_url, "output_transcript_url": transcript_url,
                "output_result_url": full_output_url, "converted_audio_output_url": converted_audio_output_url}
        response = self._post_request(url=f'{self.base_url}/predict', data=data)
        logger.info(f"Got result from speech to text service -{response.status_code}- {response.content}")
        # SpeechToTextResponseDTO(response.json())
        return response.json()

    def speech_to_text(self, *, audio_url: str, language:str = "en"):
        data = {"audio_url": audio_url,"language":language}
        response = self._post_request(url=f'{self.base_url}/predict/v2', data=data)
        logger.info(f"Got result from speech to text service -{response.status_code}- {response.content}")
        result = response.json()
        transcript = result["transcript"]
        timed_words = []
        for word in result["timed_words"]:
            timed_words.append(WordInTranscript(word=word.get("text"),
                                                start=word.get("start"),
                                                end=word.get("end"),
                                                confidence=word.get("confidence")))
        return SpeechToTextResponse(transcript=transcript, timed_words=timed_words)


@dataclasses.dataclass
class WordInTranscript:
    word:str
    start:float
    end:float
    confidence:float


@dataclasses.dataclass
class SpeechToTextResponse:
    transcript:str
    timed_words: typing.List[WordInTranscript]


class DeepgramWhisperService:

    def __init__(self):
        self.deepgram_client = Deepgram("90c4d5e8e144c567ddc08dc93cadd05cd0a6c95f")

    def speech_to_text(self, *, audio_url:str) -> SpeechToTextResponse:
        source = {
            'url': audio_url
        }
        response = self.deepgram_client.transcription.sync_prerecorded(source,
            {
                'smart_format': True,
                'model': 'whisper-large',
                'filler_words': True
            }
            )
        relevant_result = response["results"]["channels"][0]["alternatives"][0]
        transcript = relevant_result["transcript"]
        timed_words=[]
        for word in relevant_result["words"]:
            timed_words.append(WordInTranscript(word=word.get("word"),
                             start=word.get("start"),
                             end=word.get("end"),
                             confidence=word.get("confidence")))
        return SpeechToTextResponse(transcript=transcript,timed_words=timed_words)



# import asyncio
# azure_obj = AzureStorageService()
# url=azure_obj.generate_quick_read_url(container_name="tst",blob_name="22034211060_Gavit Nitin.wav")
# asyncio.run(DeepgramWhisperService().speech_to_text(
#         audio_url=url))
