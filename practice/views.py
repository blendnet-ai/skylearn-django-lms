import logging
from datetime import datetime, timedelta

from django.db.models import Max
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.dateformat import DateFormat
from evaluation.models import UserAttemptResponseEvaluation
from data_repo.models import QuestionBank
from practice.constants import MAX_QUESTION_LENGTH, MIN_QUESTION_LENGTH
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from custom_auth.authentication import FirebaseAuthentication, HardcodedAuthentication
from data_repo.providers.question_bank_provider import QuestionBankProvider
from django.http import HttpResponseBadRequest
from evaluation.event_flow.core.orchestrator import Orchestrator
from evaluation.event_flow.helpers.commons import get_eventflow_type_from_question_type
from evaluation.providers.providers import EvaluationUtility
from evaluation.seriailzers import UserAttemptResponseEvaluationSerializer
from practice.permissions import UserPracticeHistoryPermission
from practice.providers.providers import StreakUtility, TransformResponse, AudioURLProvider
from practice.providers.streak import StreakHelper
from practice.serializers import ResponseReviewSerializer
from storage_service.azure_storage import AzureStorageService
from practice.providers.timezone import TimeZone

from .models import UserAttemptedQuestionResponse, UserQuestionAttempt
from practice.providers.history import QuestionHistoryHelper
from practice.providers.word_of_day import WordOfTheDayProvider

logger = logging.getLogger(__name__)

class LogTestView(APIView):

    permission_classes = [IsAuthenticated]
    # authentication_classes = [HardcodedAuthentication]

    def get(self, request, format=None):
        logger.info("Test log to test all what all is logged")
        return Response({"data": "Success"}, status=status.HTTP_200_OK)

class PracticeQuestionView(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):

        azstsr = AzureStorageService()

        # Get the flag from query parameters
        flag = request.query_params.get('upload_hardcoded_audio', None)

        # Get type from query parameters
        question_type = request.query_params.get('type')

        num_questions = 1

        # Use the QuestionBankUtility to get the specified number of random questions
        random_questions = QuestionBankProvider.get_random_questions(num_questions, question_type)

        # Handle the case when there are no random questions
        if not random_questions:
            return Response({"data": []}, status=status.HTTP_404_NOT_FOUND)

        response_data = []
        for random_question in random_questions:

            # Create a user attempt
            user_question_attempt = UserQuestionAttempt.objects.create(
                user_id=request.user.id,  # Username as userid
                attempt_status=UserQuestionAttempt.AttemptStatus.NOT_ATTEMPTED  # 'Not Attempted'
            )

            # Create evaluation from evaluation app
            # Get evaluation id and store in evaluation_id
            evaluation_id = EvaluationUtility.create_evaluation_and_return_id()

            # Create a user attempted question response
            user_attempted_response = UserAttemptedQuestionResponse.objects.create(
                user_question_attempt=user_question_attempt,
                question_text=random_question.question if random_question else None,
                question_type=random_question.type if random_question else None,
                audio_filename='audio.wav', # TODO: take audio filename from frontend
                evaluation_id=evaluation_id
            )

            # Create SAS url
            audio_path = user_attempted_response.audio_path
            audio_url = azstsr.generate_blob_access_url(container_name='tst', blob_name=audio_path, expiry_time=datetime.now()+timedelta(hours=10), allow_read=True, allow_write=True)

            # If flag is not none upload hardcoded audio to storage for audiopath
            if flag:
                copy_operation = azstsr.copy_blob(source_container_name='hardcodedaudio', source_blob_name='audio.wav', destination_container_name='tst', destination_blob_name=audio_path)
                if copy_operation.get('copy_status') == 'success':
                    logger.info("Hardcoded audio uploaded successfully")
                else:
                    logger.error("Hardcoded audio upload failed")

            # Prepare the response data
            question_data = {
                "question": random_question.question if random_question else None,
                "type": random_question.type if random_question else None,
                "audio_url": audio_url,
                "id": user_attempted_response.id if user_attempted_response else None,
                "time_limit": random_question.response_timelimit,
                "hints": random_question.hints
            }
            response_data.append(question_data)

        return Response({"data": response_data}, status=status.HTTP_200_OK)


class SubmitCustomPracticeQuestionView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]
    
    def post(self, request):
        question_text = request.data.get("question_text")

        if question_text is None:
            return HttpResponseBadRequest("Question text was not supplied in the request body.")

        question_length = len(question_text)
        if question_length < MIN_QUESTION_LENGTH or question_length > MAX_QUESTION_LENGTH:
            return HttpResponseBadRequest(f"Question text length must be between {MIN_QUESTION_LENGTH} and {MAX_QUESTION_LENGTH}.")

        user_question_attempt = UserQuestionAttempt.objects.create(
                user_id=request.user.id,
                attempt_status=UserQuestionAttempt.AttemptStatus.NOT_ATTEMPTED
            )

        evaluation_id = EvaluationUtility.create_evaluation_and_return_id()

        user_attempted_response = UserAttemptedQuestionResponse.objects.create(
            user_question_attempt=user_question_attempt,
            question_text=question_text,
            question_type=QuestionBank.QuestionType.USER_CUSTOM_QUESTION,
            evaluation_id=evaluation_id
        )

        az_storage_service = AzureStorageService()
        audio_path = user_attempted_response.audio_path
        container_name = AudioURLProvider.get_storage_container_name()
        audio_url = az_storage_service.generate_blob_access_url(container_name=container_name, blob_name=audio_path, expiry_time=datetime.now()+timedelta(hours=1), allow_read=True, allow_write=True)

        response = {
            "audio_url": audio_url,
            "question_id": user_attempted_response.id,
        }

        return Response(response)


class SubmitQuestionView(APIView):

    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def post(self, request, practice_question_id, format=None):
        # Get user id from request
        user_id = request.user.id

        # Get the UserAttemptedQuestionResponse based on practice_question_id
        user_response_data = get_object_or_404(UserAttemptedQuestionResponse, id=practice_question_id)

        if user_response_data.evaluation_data is not None:
            eventflow_id = user_response_data.evaluation_data.get("eventflow_id")
            if eventflow_id:
                return Response({
                'message': f'Practice question response submitted successfully, id: {eventflow_id}',
                }, status=status.HTTP_208_ALREADY_REPORTED)

        # Retrieve the user_question_attempt_id
        user_question_attempt_id = user_response_data.user_question_attempt.pk

        try:
            user_question_attempt = UserQuestionAttempt.objects.get(pk=user_question_attempt_id)
            user_question_attempt.attempt_status = UserQuestionAttempt.AttemptStatus.ATTEMPT_COMPLETED
            # streak = StreakUtility.get_streak(user_id=user_id)
            user_question_attempt.daily_streak = StreakHelper.get_latest_streak(user_id=request.user.id)
            user_question_attempt.save()
        except UserQuestionAttempt.DoesNotExist:
            error_message = "User question attempt not found."
            # logger.error(error_message)
            return Response({'error': error_message}, status=status.HTTP_404_NOT_FOUND)

        dt_append=datetime.now().strftime('%d|%m-%H:%M')
        ef_type = get_eventflow_type_from_question_type(user_response_data.question_type)
        eventflow_id = Orchestrator.start_new_eventflow(eventflow_type=ef_type,
                                                        root_args={"audio_blob_path":user_response_data.audio_path,
                                                                   "converted_audio_blob_path": user_response_data.converted_audio_path,
                                                           "base_storage_path":f"sanchit_tst/{dt_append}",
                                                           "storage_container_name": "tst",
                                                           "evaluation_id": str(user_response_data.evaluation_id),
                                                           "question":user_response_data.question_text,
                                                           "user_response_id": str(user_response_data.id),
                                                           },
                                                        initiated_by=str(user_response_data.pk))

        user_response_data.evaluation_data = {"eventflow_id":str(eventflow_id)}
        user_response_data.save()

        logger.info(f"[SubmitQuestionView] started event flow with id: {eventflow_id}, pq_id: {practice_question_id}")
        response_data = {
            'message': f'Practice question response submitted successfully, id: {eventflow_id}',
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PracticeQuestionEvaluation(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, practice_question_id, format=None):
        # Get the practice_question_id from request body
        # practice_question_id = request.data.get('practice_question_id')

        # Get the UserAttemptedQuestionResponse based on practice_question_id
        azstsr = AzureStorageService()
        user_response_data = get_object_or_404(UserAttemptedQuestionResponse, id=practice_question_id)

        evaluation_id = user_response_data.evaluation_id
        evaluation_data = EvaluationUtility.get_evaluation_by_id(evaluation_id=evaluation_id)
        serialized_data = UserAttemptResponseEvaluationSerializer(evaluation_data)

        # Generate audio url for playback functionality
        audio_path = user_response_data.audio_path
        container_name = AudioURLProvider.get_storage_container_name()
        audio_url = azstsr.generate_blob_access_url(container_name=container_name, blob_name=audio_path, expiry_time=datetime.now()+timedelta(hours=1), allow_read=True, allow_write=False)
        response_data = TransformResponse.transform_evaluation_response(serialized_data.data, audio_url)

        return Response(response_data, status=status.HTTP_200_OK)


class PracticeQuestionHistory(APIView):
    permission_classes = [IsAuthenticated, UserPracticeHistoryPermission]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, user_id=None, format=None):

        if user_id is None:
            user_id = request.user.id

        attempt_data = []

        # Filter question based on type given by frontend
        question_type = request.query_params.get('type')

        # Fetch relevant data from UserQuestionAttempt for the provided user ID
        question_attempts = UserQuestionAttempt.objects.filter(user_id=user_id, attempt_status='AC').order_by('-created_at')


        if not question_attempts.exists():
            return Response("No practice attempts found for this user.", status=status.HTTP_404_NOT_FOUND)

        # Calculate total number of tests taken
        total_tests_taken = question_attempts.count()

        # last test taken date
        last_test_taken = question_attempts.aggregate(Max('created_at'))['created_at__max']

        last_test_taken = TimeZone.change_timezone(last_test_taken)

        formatted_last_test_taken = last_test_taken.strftime('%d %B %Y %I:%M %p')

        attempt_data = QuestionHistoryHelper.get_user_question_history(user_id=user_id, question_type=question_type)

        response_data = {
            "total_tests_taken": total_tests_taken,
            "last_test_taken": formatted_last_test_taken if last_test_taken else None,
            "practice_history": attempt_data,
        }

        return Response(response_data, status=status.HTTP_200_OK)


class PracticeSummaryStats(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):

        # Daily streak update

        # Average score we get from the db
        user_id = request.user.id
        daily_streak = StreakHelper.get_last_streak(user_id=user_id)
        question_attempts = UserQuestionAttempt.objects.filter(user_id=user_id, attempt_status='AC')

        test_taken = 0
        if question_attempts.exists():
            test_taken = question_attempts.count()

        response = {
            "streak": daily_streak,
            "test_taken": test_taken
        }

        return Response(response, status=status.HTTP_200_OK)


class PracticeSnapshot(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        user_id = request.user.id

        # Get the latest successful attempt for the user
        successful_attempts  = UserQuestionAttempt.objects.filter(user_id=user_id, attempt_status='AC')
        if not successful_attempts.exists():
            return Response({"detail": "No practice attempts found for this user."}, status=status.HTTP_404_NOT_FOUND)

        test_taken = successful_attempts.count()
        latest_attempt = successful_attempts.latest('created_at')

        # Get the latest attempt data
        latest_attempt_id = latest_attempt.pk
        latest_attempt_time = TimeZone.change_timezone(latest_attempt.created_at)
        latest_attempt_time = latest_attempt_time.strftime('%d %b')

        user_response_data = get_object_or_404(UserAttemptedQuestionResponse, user_question_attempt_id=latest_attempt_id)
        evaluation_id = user_response_data.evaluation_id

        # Get evaluation data
        evaluation_data = EvaluationUtility.get_evaluation_by_id(evaluation_id=evaluation_id)
        if evaluation_data:
            summary_text = None
            if evaluation_data.summary is not None:
                summary_text = evaluation_data.summary.get('text')
            response = {
                "last_attempt_id": f"Practice {test_taken}",
                "overall_score": evaluation_data.score,
                "last_attempt_timestamp": latest_attempt_time,
                "summary": summary_text,
                "highest_scoring_section": "Vocab",
                "lowest_scoring_section": "Pronunciation"
            }
            return Response({"data": response}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "No practice attempts found for this user."}, status=status.HTTP_404_NOT_FOUND)


class PracticeFluency(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, practice_question_id, format=None):
        # Get the practice_question_id from request body
        # practice_question_id = request.data.get('practice_question_id')
        # azstsr = AzureStorageService()

        # Get the UserAttemptedQuestionResponse based on practice_question_id
        user_id = request.user.id
        user_response_data = get_object_or_404(UserAttemptedQuestionResponse, id=practice_question_id)

        evaluation_id = user_response_data.evaluation_id
        evaluation_data = EvaluationUtility.get_evaluation_by_id(evaluation_id=evaluation_id)
        fluency_score = evaluation_data.fluency if evaluation_data.fluency else 0

        fluency_data = evaluation_data.fluency_details if evaluation_data.fluency_details else None
        fluency_data = TransformResponse.transform_fluency_response(fluency_data, fluency_score, user_id, practice_question_id)
        return Response({"data": fluency_data}, status=status.HTTP_200_OK)


class PracticePronunication(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, practice_question_id, format=None):
        azstr = AzureStorageService()


        # Get the UserAttemptedQuestionResponse based on practice_question_id
        user_response_data = get_object_or_404(UserAttemptedQuestionResponse, id=practice_question_id)

        # Create SAS url
        audio_path = user_response_data.audio_path
        audio_url = azstr.generate_blob_access_url(container_name='tst', blob_name=audio_path, expiry_time=datetime.now()+timedelta(hours=1), allow_read=True, allow_write=True)


        evaluation_id = user_response_data.evaluation_id
        evaluation_data = EvaluationUtility.get_evaluation_by_id(evaluation_id=evaluation_id)

        pronunciation_data = evaluation_data.pronunciation_details if evaluation_data.pronunciation_details else None
        pronunication_score = evaluation_data.pronunciation if evaluation_data.pronunciation else 0
        transform_response = TransformResponse.transform_pronunciation_response(pronunciation_data, pronunication_score, audio_url)

        return Response({"data": transform_response}, status=status.HTTP_200_OK)


class PracticeGrammar(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, practice_question_id, format=None):
        # Get the practice_question_id from request body
        # practice_question_id = request.data.get('practice_question_id')

        # Get the UserAttemptedQuestionResponse based on practice_question_id
        user_response_data = get_object_or_404(UserAttemptedQuestionResponse, id=practice_question_id)

        evaluation_id = user_response_data.evaluation_id
        evaluation_data = EvaluationUtility.get_evaluation_by_id(evaluation_id=evaluation_id)

        grammar_data = evaluation_data.grammar_details if evaluation_data.grammar_details else None
        grammar_score = evaluation_data.grammar if evaluation_data.grammar else 0
        transform_response = TransformResponse.transform_grammar_response(grammar_data, grammar_score)

        return Response({"data": transform_response}, status=status.HTTP_200_OK)


class PracticeVocab(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, practice_question_id, format=None):
        # Get the practice_question_id from request body
        # practice_question_id = request.data.get('practice_question_id')

        # Get the UserAttemptedQuestionResponse based on practice_question_id
        user_response_data = get_object_or_404(UserAttemptedQuestionResponse, id=practice_question_id)

        evaluation_id = user_response_data.evaluation_id
        evaluation_data = EvaluationUtility.get_evaluation_by_id(evaluation_id=evaluation_id)

        vocab_data = evaluation_data.vocab_details if evaluation_data.vocab_details else None

        return Response({"data": vocab_data}, status=status.HTTP_200_OK)


class PracticeWordOfTheDay(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, format=None):
        word_of_the_day = WordOfTheDayProvider.get_word_of_the_day()
        return Response(word_of_the_day, status=status.HTTP_200_OK)


class PracticeCoherence(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, practice_question_id, format=None):

        user_response_data = get_object_or_404(UserAttemptedQuestionResponse, id=practice_question_id)
        evaluation_id = user_response_data.evaluation_id
        evaluation_data = EvaluationUtility.get_evaluation_by_id(evaluation_id=evaluation_id)
        coherence_data = evaluation_data.coherence_details
        transform_response = None
        if coherence_data is not None:
            transform_response = TransformResponse.transform_coherence_response(coherence_data)

        return Response({"data": transform_response}, status=status.HTTP_200_OK)

class PracticeEmotion(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, request, practice_question_id, format=None):
        user_response_data = get_object_or_404(UserAttemptedQuestionResponse, id=practice_question_id)
        evaluation_id = user_response_data.evaluation_id
        evaluation_data = EvaluationUtility.get_evaluation_by_id(evaluation_id=evaluation_id)
        emotion_data = evaluation_data.sentiment_details
        transform_response = None
        if emotion_data is not None:
            transform_response = TransformResponse.transform_emotion_response(emotion_data)
        return Response({"data": transform_response}, status=status.HTTP_200_OK)

class PracticeReviewResponse(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [FirebaseAuthentication]

    def get(self, _, practice_question_id):
        user_response_data = get_object_or_404(UserAttemptedQuestionResponse, id=practice_question_id)
        evaluation_data = EvaluationUtility.get_evaluation_by_id(evaluation_id=user_response_data.evaluation_id)

        review_response_serializer = ResponseReviewSerializer(evaluation_data)
        return Response(review_response_serializer.data)
