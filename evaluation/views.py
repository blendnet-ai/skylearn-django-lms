from django.shortcuts import render
import logging
from datetime import datetime, timedelta
import importlib
import json
from django.db.models import Max
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.dateformat import DateFormat
from rest_framework import status
from rest_framework.permissions import IsLoggedIn
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponseBadRequest
from django.db.models import Sum
from accounts.authentication import FirebaseAuthentication
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from rest_framework.authentication import SessionAuthentication

from django.contrib.auth import get_user_model
from evaluation.assessment.assessment_classes import MockInterviewBasedRandomAssessment

from evaluation.seriailzers import (
    DSAChatHistoryQueryParamsSerializer,
    QuestionIssuesSerializer,
)

User = get_user_model()

from django.conf import settings

logger = logging.getLogger(__name__)

from ai_learning.repositories import DSAPracticeChatDataRepository

from .repositories import (
    QuestionRepository,
    AssessmentGenerationConfigRepository,
    AssessmentAttemptRepository,
    UserEvalQuestionAttemptRepository,
)
from .usecases import (
    AssessmentUseCase,
    DSAChatHistoryUseCase,
    EvaluationUseCase,
    MockInterviewReportUsecase,
    XobinUseCase,
    DSAPracticeUsecase,
    DSAReportUsecase,
    DSAQuestionsUsecase,
    QuestionIssueUsecase,
    DSAPracticeReportHistoryUsecase,
    DashBoardDetailsUsecase,
    DSASheetsConfigUsecase,
    AssessmentExpiredException,
)
from .models import AssessmentAttempt, DSAPracticeChatData

module_name = "evaluation.assessment.assessment_classes"
module = importlib.import_module(module_name)
from accounts.permissions import (
    IsLecturer,
    IsLoggedIn,
    IsStudent,
    IsSuperuser,
    firebase_drf_authentication,
)


class AssessmentDisplayData(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def get(self, request, format=None):

        user_id = request.user.id
        assessment_display_data = AssessmentUseCase.fetch_display_data(user_id)

        return Response({"data": assessment_display_data}, status=status.HTTP_200_OK)


class DashboardData(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def get(self, request, format=None):
        user_id = request.user.id

        dashboard_data = AssessmentUseCase.fetch_attempts_data(user_id)

        return Response({"data": dashboard_data}, status=status.HTTP_200_OK)


class StartAssessment(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):
        user = request.user

        data = request.data
        assessment_generation_id = data.get("assessment_generation_id")

        assessment_generation_details = data.get("assessment_generation_details", None)

        if not assessment_generation_id:
            return Response(
                {"error": "Assessment Generation ID not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            generated_assessment_data = AssessmentUseCase.create_new_assessment(
                assessment_generation_id, user, assessment_generation_details
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)

        return Response({"data": generated_assessment_data}, status=status.HTTP_200_OK)


class GetNextQuestion(APIView):

    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):

        assessment_id = request.query_params.get("assessment_id")
        user_id = request.user.id

        question_id = AssessmentUseCase.fetch_next_question_id(assessment_id, user_id)

        if question_id == 0:
            return Response(
                {"error": "Assessment completed"}, status=status.HTTP_200_OK
            )
        if not question_id:
            return Response(
                {"error": "Next question fetching failed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assessment = AssessmentUseCase.fetch_assessment_data_and_assert_validity(
            assessment_id, user_id
        )
        if not assessment:
            return Response(
                {"error": "Invalid assessment_attempt"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        question_data = AssessmentUseCase.fetch_question_data(
            question_id, assessment, user_id
        )
        if not question_data:
            return Response(
                {"error": "Invalid question id"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response({"data": question_data}, status=status.HTTP_200_OK)


class FetchQuestion(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def get(self, request, format=None):
        assessment_id = request.query_params.get("assessment_id")
        question_id = int(request.query_params.get("question_id"))

        user = request.user
        user_id = user.id

        try:
            assessment = AssessmentUseCase.fetch_assessment_data_and_assert_validity(
                assessment_id, user_id
            )
        except AssessmentExpiredException as e:
            return Response({"error": str(e)}, status=status.HTTP_410_GONE)

        if not assessment:
            return Response(
                {"error": "Invalid assessment_attempt"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        assessment_question_check = (
            AssessmentUseCase.check_if_question_exists_in_assessment(
                assessment_id, question_id, user_id
            )
        )
        if not assessment_question_check:
            return Response(
                {"error": "Question not in assessment"},
                status=status.HTTP_404_NOT_FOUND,
            )

        question_data = AssessmentUseCase.fetch_question_data(
            question_id, assessment, user
        )
        if not question_data:
            return Response(
                {"error": "Invalid question id"}, status=status.HTTP_400_BAD_REQUEST
            )
        question_data["is_superuser"] = request.user.is_superuser
        return Response({"data": question_data}, status=status.HTTP_200_OK)


class FetchAssessmentData(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        assessment_id = request.query_params.get("assessment_id")
        user_id = request.user.id

        assessment_data = AssessmentAttemptRepository.fetch_assessment_questions(
            assessment_id, user_id
        )

        return Response({"data": assessment_data}, status=status.HTTP_200_OK)


class FetchAssessmentHistory(APIView):
        
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        user_id = request.user.id

        assessment_history = AssessmentUseCase.fetch_history_data(user_id)

        return Response({"data": assessment_history}, status=status.HTTP_200_OK)


class FetchAssessmentState(APIView):
        
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        assessment_id = request.query_params.get("assessment_id")
        user_id = request.user.id

        assessment_state = AssessmentAttemptRepository.fetch_assessment_state(
            assessment_id, user_id
        )
        if not assessment_state:
            return Response(
                {"error": "Invalid assessment_attempt"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            "attempted_questions" in assessment_state
            and assessment_state["attempted_questions"]
        ):
            for question in assessment_state["attempted_questions"]:
                if question.get("code_stubs"):
                    question_id = question["question_id"]
                    code_stubs = DSAQuestionsUsecase.get_code_stubs(
                        question_id, assessment_id, request.user
                    )
                    question["original_code_stubs"] = code_stubs

        return Response({"data": assessment_state}, status=status.HTTP_200_OK)


class FetchScorecard(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        user_id = request.user.id

        scorecard = AssessmentUseCase.fetch_scorecard(user_id)

        return Response({"data": scorecard}, status=status.HTTP_200_OK)


class FetchIndividualScorecard(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        assessment_id = request.query_params.get("assessment_id")

        if not assessment_id:
            return Response(
                {"error": "Assessment ID not provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            scorecard = AssessmentUseCase.fetch_assessment_scorecard_by_id(
                assessment_id
            )
        except AssessmentAttempt.DoesNotExist:
            return Response(
                {"error": "Assessment attempt not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({"data": scorecard}, status=status.HTTP_200_OK)


class SubmitAssessmentAnswerMCQ(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):
        data = request.data
        user = request.user

        question_id = data.get("question_id")
        mcq_answer = data.get("mcq_answer")
        assessment_id = data.get("assessment_id")
        section = data.get("section")

        try:
            EvaluationUseCase.save_question_attempt(
                assessment_id, user, question_id, section, "mcq_answer", mcq_answer
            )
        except AssessmentExpiredException as e:
            return Response({"error": str(e)}, status=status.HTTP_410_GONE)

        return Response({"data": "Answer submitted"}, status=status.HTTP_200_OK)


class SubmitAssessmentAnswerMMCQ(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):

        data = request.data
        user = request.user

        question_id = data.get("question_id")
        multiple_mcq_answer = data.get("multiple_mcq_answer")
        assessment_id = data.get("assessment_id")
        section = data.get("section")

        try:
            EvaluationUseCase.save_question_attempt(
                assessment_id,
                user,
                question_id,
                section,
                "multiple_mcq_answer",
                multiple_mcq_answer,
            )
        except AssessmentExpiredException as e:
            return Response({"error": str(e)}, status=status.HTTP_410_GONE)

        return Response({"data": "Answer submitted"}, status=status.HTTP_200_OK)


class SubmitAssessmentAnswerSubjective(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):

        data = request.data
        user = request.user

        question_id = data.get("question_id")
        answer_text = data.get("answer_text")
        assessment_id = data.get("assessment_id")
        section = data.get("section")

        try:
            EvaluationUseCase.save_question_attempt(
                assessment_id, user, question_id, section, "answer_text", answer_text
            )
        except AssessmentExpiredException as e:
            return Response({"error": str(e)}, status=status.HTTP_410_GONE)

        return Response({"data": "Answer submitted"}, status=status.HTTP_200_OK)


class SubmitAssessmentAnswerVoice(APIView):
        
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):

        data = request.data
        user = request.user

        question_id = data.get("question_id")
        assessment_id = data.get("assessment_id")
        section = data.get("section")

        try:
            EvaluationUseCase.save_question_attempt(
                assessment_id, user, question_id, section, "voice"
            )
        except AssessmentExpiredException as e:
            return Response({"error": str(e)}, status=status.HTTP_410_GONE)

        return Response({"data": "Answer submitted"}, status=status.HTTP_200_OK)

class CloseAssessment(APIView):    
        
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):
        data = request.data
        user = request.user

        assessment_id = data.get("assessment_id")

        assessment = AssessmentUseCase.fetch_assessment_data_and_assert_validity(
            assessment_id, user
        )
        if not assessment:
            return Response(
                {"error": "Invalid assessment_attempt"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # EvaluationUseCase.update_activity_data(user.id)

        EvaluationUseCase.evaluate_all_questions(assessment)

        return Response({"data": "Assessment completed"}, status=status.HTTP_200_OK)


class ExitAssessment(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):
        data = request.data
        user_id = request.user.id

        assessment_id = data.get("assessment_id")

        assessment = AssessmentUseCase.fetch_assessment_data_and_assert_validity(
            assessment_id, user_id
        )
        if not assessment:
            return Response(
                {"error": "Invalid assessment_attempt"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        AssessmentUseCase.exit_assessment(assessment)
        return Response({"data": "Assessment exited"}, status=status.HTTP_200_OK)


class XobinResultWebhook(APIView):

    permission_classes = []
    authentication_classes = []

    def post(self, request, format=None):
        data = request.data
        logger.info(f"Xobin Webhook received with payload: {data}")
        hmac_header = request.headers.get("x-xobin-signature")
        logger.info(f"Received HMAC header: {hmac_header}")

        if XobinUseCase.verify_webhook(data, hmac_header):
            logger.info("Webhook verified successfully")
            XobinUseCase.save_xobin_result(data)
            return Response(
                {"data": "Webhook received and verified"}, status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "Unauthorized request"}, status=status.HTTP_401_UNAUTHORIZED
            )


class AzureStorageURL(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):

        user_id = request.user.id
        file_name = request.query_params.get("file_name")
        url = AssessmentUseCase.fetch_resume_storage_saas_url(user_id, file_name)

        return Response({"data": url}, status=status.HTTP_200_OK)


class DSAExecute(APIView):
    
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request, format=None):

        user = request.user
        question_id = request.data.get("question_id")
        assessment_id = request.data.get("assessment_attempt_id")
        type_of_evaluation = request.data.get("type_of_evaluation")
        language = request.data.get("language")
        code = request.data.get("code")
        custom_testcases = request.data.get("custom_testcases", [])

        if type_of_evaluation == "run":
            DSAPracticeUsecase.call_executor(
                user,
                question_id,
                assessment_id,
                type_of_evaluation,
                language,
                code,
                custom_testcases,
            )
            return Response(
                {"data": "Code execution started"}, status=status.HTTP_200_OK
            )

        elif type_of_evaluation == "submit":
            DSAPracticeUsecase.call_executor(
                user,
                question_id,
                assessment_id,
                type_of_evaluation,
                language,
                code,
                custom_testcases,
            )
            # execution_status_data = DSAPracticeUsecase.get_execution_status(user=user, assessment_id=assessment_id,
            #                                                                 question_id=question_id).get('test_cases')
            return Response(
                {"data": "Code execution started"}, status=status.HTTP_200_OK
            )
            # if all(test_case['passed'] for test_case in execution_status_data):
            #     DSAPracticeUsecase.call_executor(user,question_id,assessment_id,type_of_evaluation,language,code,custom_testcases)
            #     return Response({"data": "Code execution started"}, status=status.HTTP_200_OK)
            # else:
            #     error_message = "All test cases have not passed"
            #     return Response({"error": error_message}, status=status.HTTP_400_BAD_REQUEST)

        else:
            return Response(
                {"error": "Invalid Submit Type"}, status=status.HTTP_400_BAD_REQUEST
            )


class DSAExecutionStatus(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]
    def get(self, request,format=None):
        user = request.user
        question_id = request.query_params.get("question_id")
        assessment_id = request.query_params.get("assessment_attempt_id")
        data = DSAPracticeUsecase.get_execution_status(
            user=user, assessment_id=assessment_id, question_id=question_id
        )
        return Response({"data": data}, status=status.HTTP_200_OK)


class DSAChatHistory(APIView):

    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, _=None):
        query_params_serializer = DSAChatHistoryQueryParamsSerializer(
            data=request.query_params
        )

        if not query_params_serializer.is_valid():
            return Response(
                query_params_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        user_id = request.user.id
        assessment_attempt_id = query_params_serializer.validated_data["assessment_id"]
        question_id = query_params_serializer.validated_data["question_id"]

        chat_history = DSAChatHistoryUseCase.get_chat_history(
            is_superuser=request.user.is_superuser,
            user_id=user_id,
            question_id=question_id,
            assessment_attempt_id=assessment_attempt_id,
        )

        return Response({"data": chat_history}, status=status.HTTP_200_OK)


class DSAFullChatHistory(APIView):

    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, _=None):
        if not request.user.is_superuser:
            return Response(
                {"detail": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN
            )

        query_params_serializer = DSAChatHistoryQueryParamsSerializer(
            data=request.query_params
        )

        if not query_params_serializer.is_valid():
            return Response(
                query_params_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        user_id = request.user.id
        assessment_attempt_id = query_params_serializer.validated_data["assessment_id"]
        question_id = query_params_serializer.validated_data["question_id"]

        chat_history = DSAChatHistoryUseCase.get_full_chat_history(
            user_id=user_id,
            question_id=question_id,
            assessment_attempt_id=assessment_attempt_id,
        )

        return Response({"data": chat_history}, status=status.HTTP_200_OK)


class DSAReport(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, _=None):
        user_id = request.user.id
        assessment_attempt_id = request.query_params.get("assessment_id")
        attempt = AssessmentAttemptRepository.fetch_assessment_attempt(
            assessment_attempt_id
        )

        if not attempt:
            return Response(
                {"error": "Assessment attempt not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not attempt.question_list or not attempt.question_list[0]["questions"]:
            return Response(
                {"error": "No questions found in the assessment attempt"},
                status=status.HTTP_404_NOT_FOUND,
            )

        question_id = attempt.question_list[0]["questions"][0]

        question = QuestionRepository.fetch_question(question_id)
        if not question:
            return Response(
                {"error": "Question details not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        report = DSAReportUsecase.generate_report(
            user=request.user, attempt=attempt, question=question
        )

        return Response({"data": report}, status=status.HTTP_200_OK)


class BaseDSAQuestionsList(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get_dsa_questions(self, request, is_lab=False):
        user = request.user
        dsa_questions_response = DSAQuestionsUsecase.get_question_list(user, is_lab)
        return Response(
            {"data": dsa_questions_response.__dict__}, status=status.HTTP_200_OK
        )


class DSAQuestionsList(BaseDSAQuestionsList):
    def get(self, request):
        return self.get_dsa_questions(request)


class DSALabQuestionsList(BaseDSAQuestionsList):
    def get(self, request):
        return self.get_dsa_questions(request, is_lab=True)


class DSAPracticeAttemptGenerator(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request):
        user = request.user
        mode = request.query_params.get("mode")
        questions_id = request.query_params.get("question_id")
        generated_assessment_data = DSAQuestionsUsecase.generate_attempt_by_question_id(
            user, questions_id, mode
        )
        return Response({"data": generated_assessment_data}, status=status.HTTP_200_OK)


class QuestionIssueReport(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def post(self, request):
        user = request.user
        question_serializer = QuestionIssuesSerializer(data=request.data)

        if not question_serializer.is_valid():
            return Response(
                question_serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

        question_issue_id = QuestionIssueUsecase.create_issue(
            user=user,
            assessment_attempt_id=question_serializer.validated_data[
                "assessment_attempt_id"
            ],
            type_of_issue=question_serializer.validated_data["type_of_issue"],
            question_id=question_serializer.validated_data["question_id"],
            description=question_serializer.validated_data["description"],
        )

        return Response(
            {"data": f"Issue created {question_issue_id}"},
            status=status.HTTP_201_CREATED,
        )


class DSAPracticeReportHistory(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request):
        user = request.user
        practice_history = DSAPracticeReportHistoryUsecase.get_dsa_reports(
            user_id=user.id
        )
        return Response({"data": practice_history}, status=200)


class FetchDashboardDetails(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request):
        user = request.user
        data = DashBoardDetailsUsecase.get_dashboard_details(user_id=user.id)
        return Response({"data": data}, status=status.HTTP_200_OK)


class DSASheetList(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request):
        user = request.user
        sheet_id = request.query_params.get("id")
        sheet_questions_response = DSASheetsConfigUsecase.get_sheet_questions(
            user=user, sheet_id=sheet_id
        )
        sheet_status_response = DSASheetsConfigUsecase.get_sheet_status(
            user=user, sheet_id=sheet_id
        )
        return Response(
            {
                "data": {
                    **sheet_questions_response.__dict__,
                    "sheet_status": sheet_status_response,
                }
            },
            status=status.HTTP_200_OK,
        )


class DSAAssessmentChatHistoryView(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [SessionAuthentication]

    @method_decorator(login_required)
    def get(self, request, **kwargs):
        assessment_id = kwargs.get("assessment_id")
        if request.user.is_staff:
            chat_data = DSAPracticeChatDataRepository.get_chat_data_by_assessment_id(
                assessment_id=assessment_id
            )
            return render(
                request,
                "chat_history.html",
                {"chat_data": chat_data, "assessment_id": assessment_id},
            )
        else:
            return render(
                request,
                "error.html",
                {"error_message": "Only staff members can access chat history."},
            )


class AvailableInterviewTypesView(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request):
        data = MockInterviewBasedRandomAssessment.get_assessment_generation_configs()
        return Response({"data": data}, status=status.HTTP_200_OK)


class MockInterviewBehaviouralReportView(APIView):
    permission_classes = [IsLoggedIn]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, _=None):
        user_id = request.user.id
        assessment_attempt_id = request.query_params.get("assessment_id")
        attempt = AssessmentAttemptRepository.fetch_assessment_attempt(
            assessment_attempt_id
        )

        if not attempt:
            return Response(
                {"error": "Assessment attempt not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not attempt.question_list or not attempt.question_list[0]["questions"]:
            return Response(
                {"error": "No questions found in the assessment attempt"},
                status=status.HTTP_404_NOT_FOUND,
            )

        report = MockInterviewReportUsecase.generate_behavioural_report(
            user=request.user, attempt=attempt
        )

        return Response({"data": report}, status=status.HTTP_200_OK)
