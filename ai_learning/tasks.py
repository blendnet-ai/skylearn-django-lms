from celery import shared_task
from django.core.files import File
import os

from .transcript_chapter_creator import AILearning
prompt_library = AILearning()

@shared_task
def task1():
    youtube_url ="https://www.youtube.com/watch?v=p9dGcWoX3vU%26ab_channel=DailyDoseOfInternet"
    print(youtube_url)
    save_to_file(youtube_url, 'url1.txt')
    prompt_library.initialize(url=youtube_url)
    transcript = prompt_library.fetch_transcript()
    save_to_file(transcript, 'task1.txt')
    # task2.delay(transcript)

@shared_task
def task2(transcript):
    chapters_data = prompt_library.create_chapters(transcript)

@shared_task
def task3(converted_string):
    converted_string += '\n'
    save_to_file(converted_string, 'task3.txt')

def save_to_file(data, filename):
    with open(filename, 'w') as f:
        f.write(data)
