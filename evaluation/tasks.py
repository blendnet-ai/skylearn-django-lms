import logging

from celery import shared_task

from evaluation.event_flow.processors.assessment_evaluator import AssessmentEvaluatorProcessor
from evaluation.event_flow.processors.speaking_final_score import SpeakingFinalScore
from evaluation.event_flow.processors.writing_final_score import WritingFinalScore
from evaluation.repositories import AssessmentAttemptRepository
from evaluation.models import AssessmentAttempt
import openai

from config.celery import app

logger = logging.getLogger(__name__)


@shared_task
def add(*, x, y):
    return x + y


# Don't use below method of decoractor retry i
#@app.task(
#             bind=True,
#           # default_retry_delay=5,
#           autoretry_for=(openai.RateLimitError,),
#           retry_backoff=30,
#           retry_backoff_max=300,
#           max_retries=3,
#           # retry_jitter=True,
#           ignore_result=True)
@app.task(bind=True, max_retries=5)
def call_event_processor(self, *, eventflow_id, processor_name, inputs, root_arguments):
    from evaluation.event_flow.processors.fluency import Fluency
    from evaluation.event_flow.processors.awkward_pauses import AwkwardPauses
    from evaluation.event_flow.processors.ielts_report_generator import IELTSReportGenerator
    from evaluation.event_flow.processors.interview_prep_report_generator import InteviewPrepReportGenerator
    from evaluation.event_flow.processors.filler_words import FillerWords
    from evaluation.event_flow.processors.pace import Pace
    from evaluation.event_flow.processors.code_efficiency_processor import CodeEfficiencyProcessor
    from evaluation.event_flow.processors.code_improvement_processor import CodeImprovementProcessor
    from evaluation.event_flow.processors.code_quality_processor import CodeQualityProcessor
    from evaluation.event_flow.processors.code_summary_processor import CodeSummaryProcessor
    from evaluation.event_flow.processors.code_revision_topic_processor import CodeRevisionTopicProcessor
    from evaluation.event_flow.processors.mock_behaviour_final_score import MockBehaviourFinalScore
    from evaluation.event_flow.processors.pitch import Pitch
    from evaluation.event_flow.processors.pronunciation import Pronunciation
    from evaluation.event_flow.processors.vocab import Vocab
    from evaluation.event_flow.processors.testingProcessor import TestingProcessor
    from evaluation.event_flow.processors.db_saver_processors import (
        CoherenceSaver,
        PronunciationSaver,
        FluencySaver,
        VocabSaver,
        IELTSGrammarSaver,
        InterviewPrepGrammarSaver,
        SentimentSaver,
        IELTSEvaluationSaver,
        InterviewEvaluationSaver,
        IELTSIdealResponseSaver,
        InterviewPrepIdealResponseSaver,
        SpeakingSaver,
        WritingSaver,
        DSAResponseSaverEfficiency,
        DSAResponseSaverImprovement,
        DSAResponseSaverQuality,
        DSAResponseSaverRevision,
        DSAResponseSaverSummary,
        DSAMarkAsCompleteSaver,
         MockBehaviouralSaver
    )
    from evaluation.event_flow.processors.coherence import Coherence
    from evaluation.event_flow.processors.grammar import Grammar
    from evaluation.event_flow.processors.interview_prep_grammar import InterviewPrepGrammar
    from evaluation.event_flow.processors.speech_to_text import SpeechToText
    from evaluation.event_flow.processors.sentiment import Sentiment
    from evaluation.event_flow.processors.termination_processors import AbortHandler
    from evaluation.event_flow.processors.ideal_response_processors import (
        IELTSIdealResponse,
        InterviewPrepIdealResponse,
    )
    logger.info(f"Task {self.__dict__}")
    processors = [
        SpeechToText,
        Pace,
        Coherence,
        Fluency,
        FillerWords,
        Vocab,
        Pronunciation,
        Grammar,
        InterviewPrepGrammar,
        Pitch,
        CoherenceSaver,
        PronunciationSaver,
        FluencySaver,
        VocabSaver,
        IELTSGrammarSaver,
        InterviewPrepGrammarSaver,
        SentimentSaver,
        IELTSReportGenerator,
        IELTSEvaluationSaver,
        InteviewPrepReportGenerator,
        InterviewEvaluationSaver,
        AwkwardPauses,
        Sentiment,
        AbortHandler,
        IELTSIdealResponse,
        InterviewPrepIdealResponse,
        IELTSIdealResponseSaver,
        InterviewPrepIdealResponseSaver,
        SpeakingSaver,
        WritingSaver,
        SpeakingFinalScore,
        WritingFinalScore,
        AssessmentEvaluatorProcessor,
        CodeEfficiencyProcessor,
        CodeQualityProcessor,
        CodeImprovementProcessor,
        CodeRevisionTopicProcessor,
        CodeSummaryProcessor,
        TestingProcessor,
        DSAResponseSaverEfficiency,
        DSAResponseSaverImprovement,
        DSAResponseSaverQuality,
        DSAResponseSaverRevision,
        DSAResponseSaverSummary,
        DSAResponseSaverEfficiency,
        DSAMarkAsCompleteSaver,
        MockBehaviouralSaver,
        MockBehaviourFinalScore
    ]

    processor_name_to_processors = {p.__name__: p for p in processors}
    processor_instance: SpeechToText = processor_name_to_processors[processor_name]
    try:
        logger.info(f"Celery calling processor class - {processor_instance}.")
        processor_instance(eventflow_id=eventflow_id, inputs=inputs, root_arguments=root_arguments).execute()
    except openai.RateLimitError as exc:
        # Doing manual retry than celery decorator because that is showing
        default_retry_delay = 10
        max_retry_delay = 600
        retry_delay = min(default_retry_delay * (2 ** self.request.retries), max_retry_delay)
        # Log the retry status
        logger.info(f"{self.request.__dict__}, [{processor_name}-celery_task]: Retry #{self.request.retries + 1} in {retry_delay} seconds.")
        # Retry with calculated delay
        self.retry(exc=exc, countdown=retry_delay)

@shared_task(queue='evaluation_queue')
def mark_test_abandoned(assessment_id, user_id):
    try:
        assessment = AssessmentAttemptRepository.get_assessment_data(assessment_id, user_id)
        if not assessment:
            logger.error(f"Assessment with ID {assessment_id} does not exist.")
        if assessment.status == int(AssessmentAttempt.Status.IN_PROGRESS):
            logger.info(f"Marking assessment with ID {assessment_id} as abandoned.")
            AssessmentAttemptRepository.add_or_update_assessment_attempt(assessment_attempt=assessment, closed = True, status = AssessmentAttempt.Status.ABANDONED)
    
    except Exception as e:
        logger.exception(f"Error while marking test as abandoned: {e}")

@shared_task(queue='evaluation_queue')
def evaluate_behavioral_assessment(eval_data,assessment_attempt_id):
    try:
        from evaluation.event_flow.processors.mock_behaviour_summary_processor import MockInterviewBehavioralProcessor

        # Instantiate the processor with all required arguments
        processor = MockInterviewBehavioralProcessor(eval_data)
        evaluation_result = processor._execute()
        assessment_attempt=AssessmentAttemptRepository.fetch_assessment_attempt(assessment_id=assessment_attempt_id)
        assessment_attempt.eval_data['overall_summary'] = evaluation_result['overall_summary']
        assessment_attempt.status = AssessmentAttempt.Status.COMPLETED
        assessment_attempt.evaluation_triggered = True
        assessment_attempt.save()


    except Exception as e:
        logger.error(f'Error in evaluating behavioral assessment: {e}')
        assessment_attempt.status = AssessmentAttempt.Status.EVALUATION_PENDING
        assessment_attempt.evaluation_triggered = False


@shared_task(queue='evaluation_queue')
def evaluate_lsrw_assessment(eval_data,assessment_attempt_id):
    try:
        from evaluation.event_flow.processors.lsrw_summary_processor import LSRW_Summary_Processor

        # Instantiate the processor with all required arguments
        processor = LSRW_Summary_Processor(eval_data)
        evaluation_result = processor._execute()
        assessment_attempt=AssessmentAttemptRepository.fetch_assessment_attempt(assessment_id=assessment_attempt_id)
        assessment_attempt.eval_data['performance_overview']['feedback'] = evaluation_result['overall_summary']
        assessment_attempt.status = AssessmentAttempt.Status.COMPLETED
        assessment_attempt.evaluation_triggered = True
        assessment_attempt.save()


    except Exception as e:
        logger.error(f'Error in evaluating behavioral assessment: {e}')
        assessment_attempt.status = AssessmentAttempt.Status.EVALUATION_PENDING
        assessment_attempt.evaluation_triggered = False