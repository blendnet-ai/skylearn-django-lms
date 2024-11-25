from django.core.management.base import BaseCommand
from django.test import RequestFactory
from practice.views import PracticeQuestionView, SubmitQuestionView, PracticeQuestionEvaluation
from rest_framework.test import force_authenticate
import json
import os
import requests
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
import traceback

def get_now() -> datetime:
    required_timezone = "Asia/Kolkata"
    return datetime.now(ZoneInfo(required_timezone))


# Set the title and text of the message

class SimpleTest:
    """
    Tests
    eval_response={'status': 'Complete',
     'summary': 'Congratulations on your performance! Your pronunciation is clear and understandable, scoring 89 out of 100. Your fluency is good, with a score of 71 out of 100. Your grammar is at an intermediate level, which is impressive. Your coherence is good, showing that you can express your ideas clearly. Your vocabulary is at an A1 level, which is a great starting point. You have very few filler words, indicating that you speak with confidence. Your pace is good, allowing your listener to follow along easily. Keep up the great work!',
     'overall_performance': 'Intermediate',
     'overall_score': 6.38,
     'evaluation_response': {'Fluency': {'score': 71.8},
      'Pronunciation': {'score': 89.8},
      'Grammar': {'score': 6.0},
      'Vocab': {'score': 'A1+'}}}


    SimpleTest().check_evaluation_response_and_send_status(question_id="54c29733-173f-4f4e-9873-51c70a98ca66",
                                                           evaluation_response=eval_response)
    SimpleTest().get_evaluation_details(question_id="54c29733-173f-4f4e-9873-51c70a98ca66")


    """
    def __init__(self):
        self.setUp()
        self.TELEGRAM_PRACTICE_FLOW_STATUS_TOKEN = "6485472828:AAE_WkOgxAGE_hNHE5cRbjFGK1y4jr1M70Q"
        self.TELEGRAM_PRACTICE_FLOW_ERROR_TOKEN = "6162441139:AAGENiIqE4brJA3nxv9TT_nv4LAd_qV0J3c"
        self.chat_id = "82535051"
        self.wait_for_evaluation_time_in_seconds = settings.TEST_EVALUATION_WAITING_TIME_IN_SECONDS
        self.admins = settings.ADMINS

    def send_telegram_msg(self, msg, error=False):
        if error:
            token = self.TELEGRAM_PRACTICE_FLOW_ERROR_TOKEN
        else:
            token = self.TELEGRAM_PRACTICE_FLOW_STATUS_TOKEN
        url = f"https://api.telegram.org/bot{token}/sendMessage?chat_id={self.chat_id}&text={msg}"
        requests.get(url).json()
        print("SENDING TELEGRAM MSG", msg)
        self.send_email_msg(msg, error)

    def send_email_msg(self, msg, error=False):
        status = "Error" if error else "Successful"
        msg = EmailMultiAlternatives(
                subject=f"{status} Practice run",
                body=msg,
                to=list(map(lambda x: x[1], self.admins))
            )
        res = msg.send()
        mail_status = "succeeded" if res == 1 else "failed"
        print(f"Sending mail {mail_status}")

    @staticmethod
    def save_to_sass_url(*, url: str, file_path: str) -> (str, int):
        file_name_only = os.path.basename(file_path)
        with open(file_path, 'rb') as fil:
            response = requests.put(url,
                                    headers={
                                        "Content-type": "audio/wav",
                                        "x-ms-blob-type": "BlockBlob"
                                    },
                                    params={"file": file_name_only},
                                    data=fil)
            return response

    def setUp(self):
        # Every test needs access to the request factory.
        self.factory = RequestFactory()
        self.user = User.objects.get(username="speechai_user")

    def test_question_submission_flow(self):
        request = self.factory.get("/api/v1/practice/questions")

        force_authenticate(request, user=self.user)

        response = PracticeQuestionView.as_view()(request)

        response.render()

        question_response = json.loads(response.content)
        question_id = question_response['data'][0]['id']
        audio_url = question_response['data'][0]['audio_url']

        self.call_submit(question_id=question_id, audio_url=audio_url)
        time.sleep(self.wait_for_evaluation_time_in_seconds)
        evaluation_response = self.get_evaluation_details(question_id=question_id)
        self.check_evaluation_response_and_send_status(question_id=question_id, evaluation_response=evaluation_response)

    def check_evaluation_response_and_send_status(self, *, question_id, evaluation_response):
        overall_score = evaluation_response.get('overall_score', 0)
        status = evaluation_response.get('status')
        if status == "Complete" and overall_score != None and overall_score > 0:
            self.send_successfull_telegram_msg(question_id=question_id)
        else:
            self.send_error_telegram_msg(question_id=question_id, evaluation_response=evaluation_response)

    def send_successfull_telegram_msg(self, *, question_id):
        msg = f"😊😊😊😊😊 Successful Practice run.\nQuestion ID= {question_id}"
        self.send_telegram_msg(msg)

    def send_error_telegram_msg(self, *, question_id, evaluation_response):
        msg = f"🤬🤬🤬🤬🤬 ERROR Practice run.\nQuestion Id - {question_id}\n"
        self.send_telegram_msg(msg)
        msg = f"🤬🤬🤬🤬🤬 ERROR Practice run.\nQuestion Id - {question_id}\n.Evaluation Response - {evaluation_response}"
        self.send_telegram_msg(msg, error=True)

    def get_evaluation_details(self, *, question_id):
        request = self.factory.get(f"/api/v1/practice/question_evaluation/{question_id}")
        force_authenticate(request, user=self.user)
        evaluation_response = PracticeQuestionEvaluation.as_view()(request, question_id)
        evaluation_response.render()
        return json.loads(evaluation_response.content)

    def call_submit(self, *, question_id, audio_url):

        request = self.factory.post(f"/api/v1/practice/submit_practice_question_response/{question_id}")
        save_resp = self.save_to_sass_url(url=audio_url, file_path="/home/appuser/code/practice/management/commands/app_audio.wav")

        print("Upload response", save_resp.content, save_resp.status_code)
        force_authenticate(request, user=self.user)
        submit_response = SubmitQuestionView.as_view()(request, question_id)
        submit_response.render()

        print("Submit response", submit_response.content, submit_response.status_code)




class Command(BaseCommand):
    help = "Runs the practice flow test and sends status/error msg on a telegram channel"

    def add_arguments(self, parser):
        pass
        # parser.add_argument("poll_ids", nargs="+", type=int)

    def handle(self, *args, **options):
        try:
            SimpleTest().test_question_submission_flow()
        except Exception as e:
            stacktrace = traceback.format_exc()
            msg = f"Practice Flow test failed. Error = {e}.\n{stacktrace}"
            SimpleTest().send_telegram_msg(msg, error=True)