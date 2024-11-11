from string import Template
import json
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService
import urllib.parse as urlparse
import sys

from youtube_transcript_api import YouTubeTranscriptApi

def is_youtube_url(url):
    parsed_url = urlparse.urlparse(url)

    if "youtube.com" not in parsed_url.netloc or "watch" not in parsed_url.path:
        return False

    return True

def get_transcript(video_id):
    transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
    transcript = transcript_list.find_transcript(['en'])
    return transcript.fetch()
def save_to_file(data, filename):
    with open(filename, 'w') as f:
        f.write(data)

class AILearning:
    def __init__(self):
        self.transcript = None
        self.url = None
        self.chapter_creation_prompt = """
        $transcript\nGiven the above transcript of a video divide it into topics.
        For each topic, generate the following
        1. Summary line about that topic
        2. Individual points talked about in that topic. DO NOT LIMIT the number of points per topic
        """

        self.question_creation_prompt = """
        $chapter_transcript
        Given the above piece of singluar chapter from the transcript from a video, generate 2-3 MCQ questions on the content. "\
        Each MCQ should have 4 options. " \
        """    

    def initialize(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def fetch_transcript(self):
        youtube_url = self.url
        save_to_file(youtube_url, 'url.txt')
        video_id = urlparse.parse_qs(urlparse.urlparse(youtube_url).query)['v'][0]
        transcript = get_transcript(video_id)
        self.transcript = transcript
        save_to_file(transcript, 'transcript1.txt')
        return transcript

    def create_chapters(self):
        src = Template(self.chapter_creation_prompt)
        result = src.substitute(transcript=self.transcript)
        llm = OpenAIService()
        messages = [{'role': 'system', 'content': result}]
        response = json.loads(llm.get_completion_from_messages(messages))
        return response

    def create_questions(self, chapter):
        src = Template(self.question_creation_prompt)
        result = src.substitute(chapter)
        llm = OpenAIService()
        messages = [{'role': 'system', 'content': result}]
        response = json.loads(llm.get_completion_from_messages(messages))
        return response
