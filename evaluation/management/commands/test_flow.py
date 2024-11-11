from django.core.management.base import BaseCommand
from django.test import RequestFactory
from evaluation.views import (
    CloseAssessment,
    DSAExecute,
    DSAPracticeAttemptGenerator,
    DSAReport,
)
from rest_framework.test import force_authenticate
import json
import time
import logging

from django.contrib.auth.models import User
from sentry_sdk import capture_exception
from django.conf import settings

logger = logging.getLogger(__name__)


class DSATest:

    class ReportGenerationException(Exception):
        pass

    _PRACTICE_MODE = 1
    _SOLUTION = """class Solution:
    def toggleBits(self, n, l, r):
        # Create a mask with bits set in the range l to r
        mask = ((1 << (r - l + 1)) - 1) << (l - 1)
        # Toggle the bits in the range by XORing n with the mask
        return n ^ mask"""

    def __init__(self):
        self.setup()
        self.wait_for_evaluation_time_in_seconds = (
            settings.TEST_EVALUATION_WAITING_TIME_IN_SECONDS
        )

        self.question_id = settings.DSA_FLOW_TEST_QUESTION_ID

    def setup(self):
        self.factory = RequestFactory()
        self.user = User.objects.get(username="speechai_user")

    def generate_practice_attempt(self, question_id):
        request = self.factory.get(
            f"/api/v1/evaluation/generate-dsa-practice-attempt?question_id={question_id}&mode={DSATest._PRACTICE_MODE}"
        )
        force_authenticate(request, user=self.user)
        response = DSAPracticeAttemptGenerator.as_view()(request)
        response.render()

        response = json.loads(response.content)

        assessment_id = response["data"]["assessment_id"]
        return assessment_id

    def submit_code(self, assessment_id, question_id):
        request_data = {
            "assessment_attempt_id": assessment_id,
            "code": DSATest._SOLUTION,
            "custom_testcases": [],
            "language": "python",
            "question_id": question_id,
            "type_of_evaluation": "run",
        }

        request_json = json.dumps(request_data)

        request = self.factory.post(
            f"/api/v1/evaluation/dsa-execute",
            data=request_json,
            content_type="application/json",
        )
        force_authenticate(request, user=self.user)
        response = DSAExecute.as_view()(request)
        response.render()

        response = json.loads(response.content)

        return response

    def close_assessment(self, assessment_id):
        request_data = {
            "assessment_id": assessment_id,
        }
        request_json = json.dumps(request_data)

        request = self.factory.post(
            f"/api/v1/evaluation/close-assessment",
            data=request_json,
            content_type="application/json",
        )

        force_authenticate(request, user=self.user)
        response = CloseAssessment.as_view()(request)
        response.render()

        response = json.loads(response.content)

        return response

    def get_report(self, assessment_id):
        request = self.factory.get(
            f"/api/v1/evaluation/dsa-practice-report?assessment_id={assessment_id}"
        )
        force_authenticate(request, user=self.user)
        response = DSAReport.as_view()(request)
        response.render()

        response = json.loads(response.content)
        report = response["data"]
        return report

    def check_report_and_raise_for_status(self, report, assessment_id):
        total_score = report["total_score"]["score"]
        if total_score is None:
            raise DSATest.ReportGenerationException(
                f"""Report not generated for assessment: {assessment_id}
                Report: {report}"""
            )

    def test_practice_submit_flow(self):

        question_id = self.question_id
        assessment_id = self.generate_practice_attempt(question_id=question_id)

        self.submit_code(assessment_id=assessment_id, question_id=question_id)
        self.close_assessment(assessment_id=assessment_id)

        logger.info(
            f"DSATest: Test run completed for assessment id {assessment_id}, will check report in {self.wait_for_evaluation_time_in_seconds} seconds"
        )

        time.sleep(self.wait_for_evaluation_time_in_seconds)

        report = self.get_report(assessment_id=assessment_id)

        self.check_report_and_raise_for_status(
            report=report, assessment_id=assessment_id
        )


class Command(BaseCommand):
    help = "Runs the dsa flow test and sends exception to sentry"

    def handle(self, *args, **options):
        try:
            logger.info(f"DSATest: Starting test run..")
            DSATest().test_practice_submit_flow()
            logger.info(f"DSATest: Test run successful")
        except Exception as e:
            logger.info(f"DSATest: Exception- {e} ")
            capture_exception(e)
