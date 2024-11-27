from practice.models import UserAttemptedQuestionResponse
from .base_event_processor import EventProcessor
from ...models import UserAttemptResponseEvaluation, UserEvalQuestionAttempt, AssessmentAttempt
import logging

logger = logging.getLogger(__name__)



class BaseGrammarSaver(EventProcessor):

    def get_processor_name(self):
        raise NotImplemented

    def initialize(self):
        self.evaluation_id = self.root_arguments.get("evaluation_id")
        process_name = self.get_processor_name()
        self.grammar_score = self.inputs[process_name]["score"]
        self.grammar_details = self.inputs[process_name]

    def _execute(self):
        self.initialize()
        eval_object = UserAttemptResponseEvaluation.objects.get(id=self.evaluation_id)
        eval_object.grammar = self.grammar_score
        eval_object.grammar_details = self.grammar_details
        eval_object.save()
        return {}

class IELTSGrammarSaver(BaseGrammarSaver):

    def get_processor_name(self):
        return "Grammar"

class InterviewPrepGrammarSaver(BaseGrammarSaver):

    def get_processor_name(self):
        return "InterviewPrepGrammar"


class VocabSaver(EventProcessor):

    def initialize(self):
        self.evaluation_id = self.root_arguments.get("evaluation_id")
        self.vocab_score = self.inputs["Vocab"]["score"]
        self.vocab_details = self.inputs["Vocab"]

    def _execute(self):
        self.initialize()
        eval_object = UserAttemptResponseEvaluation.objects.get(id=self.evaluation_id)
        eval_object.vocab = self.vocab_score
        eval_object.vocab_details = self.vocab_details
        eval_object.save()
        return {}


class PronunciationSaver(EventProcessor):

    def initialize(self):
        self.evaluation_id = self.root_arguments.get("evaluation_id")
        self.pronunciation_score = self.inputs["Pronunciation"]["score"]
        self.pronunciation_details = self.inputs["Pronunciation"]

    def _execute(self):
        self.initialize()
        eval_object = UserAttemptResponseEvaluation.objects.get(id=self.evaluation_id)
        eval_object.pronunciation = self.pronunciation_score
        eval_object.pronunciation_details = self.pronunciation_details
        eval_object.save()
        return {}


class FluencySaver(EventProcessor):

    def initialize(self):
        self.evaluation_id = self.root_arguments.get("evaluation_id")
        self.fluency_score = self.inputs["Fluency"]["score"]
        self.fluency_details = self.inputs["Fluency"]

    def _execute(self):
        self.initialize()
        eval_object = UserAttemptResponseEvaluation.objects.get(id=self.evaluation_id)
        eval_object.fluency = self.fluency_score
        eval_object.fluency_details = self.fluency_details
        eval_object.save()
        return {}


class CoherenceSaver(EventProcessor):

    def initialize(self):
        self.evaluation_id = self.root_arguments.get("evaluation_id")
        self.coherence_score = self.inputs["Coherence"]["score"]
        self.coherence_details = self.inputs["Coherence"]

    def _execute(self):
        self.initialize()
        eval_object = UserAttemptResponseEvaluation.objects.get(id=self.evaluation_id)
        eval_object.coherence = self.coherence_score
        eval_object.coherence_details = self.coherence_details
        eval_object.save()
        return {}


class BaseEvaluationSaver(EventProcessor):

    def get_process_name(self):
        raise NotImplemented


    def initialize(self):
        self.evaluation_id = self.root_arguments.get("evaluation_id")
        process_name = self.get_process_name()
        self.final_score = self.inputs[process_name]["score"]
        self.summary = self.inputs[process_name]["summary"]
        self.score_title = self.inputs[process_name]["score_title"]


    def _execute(self):
        self.initialize()
        eval_object = UserAttemptResponseEvaluation.objects.get(id=self.evaluation_id)
        eval_object.summary = {"text": self.summary, "score": self.final_score, "overall_performance":self.score_title}
        eval_object.score = self.final_score
        eval_object.status = UserAttemptResponseEvaluation.Status.COMPLETE
        eval_object.save()
        return {"summary": self.summary, "overall_score": self.final_score}

class IELTSEvaluationSaver(BaseEvaluationSaver):

    def get_process_name(self):
        return "IELTSReportGenerator"

class InterviewEvaluationSaver(BaseEvaluationSaver):

    def get_process_name(self):
        return "InteviewPrepReportGenerator"

class MockBehaviouralSaver(EventProcessor):
    def initialize(self):
        self.question_attemp_id = self.root_arguments.get("question_attempt_id")

        self.fluency_details = self.inputs["Fluency"]
        self.coherence_details = self.inputs["Coherence"]
        self.fluency_score = self.inputs["Fluency"]["score"]
        self.ideal_response_details = self.inputs["InterviewPrepIdealResponse"]
        self.coherence_score = self.inputs["MockBehaviourFinalScore"]["coherence"]
        self.sentiment_score=self.inputs["MockBehaviourFinalScore"]["sentiment"]



    def _execute(self):
        self.initialize()
        eval_object = UserEvalQuestionAttempt.objects.get(id=self.question_attemp_id)

        eval_data = {
            "fluency": {"score": self.fluency_score, "details": self.fluency_details},
            "coherence": {
                "score": self.coherence_score,
                "details": self.coherence_details,
            },
            "sentiment": {
                "score": self.sentiment_score
            },
            "ideal_response": self.ideal_response_details
        }
        eval_object.eval_data = eval_data
        eval_object.status = UserEvalQuestionAttempt.Status.EVALUATED

        eval_object.save()
        return {}
    
class SpeakingSaver(EventProcessor):
    def initialize(self):
        self.question_attemp_id = self.root_arguments.get("question_attempt_id")

        self.vocab_details = self.inputs["Vocab"]
        self.pronunciation_details = self.inputs["Pronunciation"]
        self.fluency_details = self.inputs["Fluency"]
        self.coherence_details = self.inputs["Coherence"]
        self.sentiment_details = self.inputs["Sentiment"]
        self.grammar_details = self.inputs["InterviewPrepGrammar"]

        self.final_score = self.inputs["SpeakingFinalScore"]["final_score"]
        self.grammar_score = self.inputs["SpeakingFinalScore"]["grammar"]
        self.vocab_score = self.inputs["SpeakingFinalScore"]["vocab"]
        self.coherence_score = self.inputs["SpeakingFinalScore"]["coherence"]
        self.fluency_score = self.inputs["SpeakingFinalScore"]["fluency"]
        self.pronunciation_score = self.inputs["SpeakingFinalScore"]["pronunciation"]
        self.sentiment_score = self.inputs["SpeakingFinalScore"]["sentiment"]


    def _execute(self):
        self.initialize()
        eval_object = UserEvalQuestionAttempt.objects.get(id=self.question_attemp_id)

        eval_data = {
            "final_score": self.final_score,
            "vocab": {"score": self.vocab_score, "details": self.vocab_details},
            "pronunciation": {
                "score": self.pronunciation_score,
                "details": self.pronunciation_details,
            },
            "fluency": {"score": self.fluency_score, "details": self.fluency_details},
            "coherence": {
                "score": self.coherence_score,
                "details": self.coherence_details,
            },
            "sentiment": {
                "score": self.sentiment_score,
                "details": self.sentiment_details,
            },
            "grammar": {"score": self.grammar_score, "details": self.grammar_details},
        }
        eval_object.eval_data = eval_data
        eval_object.status = UserEvalQuestionAttempt.Status.EVALUATED

        eval_object.save()
        return {}


class WritingSaver(EventProcessor):
    def initialize(self):
        self.question_attemp_id = self.root_arguments.get("question_attempt_id")

        self.vocab_details = self.inputs["Vocab"]

        self.coherence_details = self.inputs["Coherence"]

        self.grammar_details = self.inputs["InterviewPrepGrammar"]

        self.final_score = self.inputs["WritingFinalScore"]["final_score"]
        self.grammar_score = self.inputs["WritingFinalScore"]["grammar"]
        self.vocab_score = self.inputs["WritingFinalScore"]["vocab"]
        self.coherence_score = self.inputs["WritingFinalScore"]["coherence"]

    def _execute(self):
        self.initialize()
        eval_object = UserEvalQuestionAttempt.objects.get(id=self.question_attemp_id)

        eval_data = {
            "final_score": self.final_score,
            "vocab": {"score": self.vocab_score, "details": self.vocab_details},
            "coherence": {
                "score": self.coherence_score,
                "details": self.coherence_details,
            },
            "grammar": {"score": self.grammar_score, "details": self.grammar_details},
        }
        eval_object.eval_data = eval_data
        eval_object.status = UserEvalQuestionAttempt.Status.EVALUATED

        eval_object.save()
        return {}
    

class SentimentSaver(EventProcessor):

    def initialize(self):
        self.evaluation_id = self.root_arguments.get("evaluation_id")
        self.sentiment_score = self.inputs["Sentiment"]["sentiment"]
        self.sentiment_details = self.inputs["Sentiment"]

    def _execute(self):
        self.initialize()
        eval_object = UserAttemptResponseEvaluation.objects.get(id=self.evaluation_id)
        eval_object.sentiment = self.sentiment_score
        eval_object.sentiment_details = self.sentiment_details
        eval_object.save()
        return {}
    

class BaseIdealResponseSaver(EventProcessor):

    def get_processor_name(self):
        raise NotImplementedError

    def initialize(self):
        processor_name = self.get_processor_name()
        self.evaluation_id = self.root_arguments.get("evaluation_id")
        self.ideal_response_details = self.inputs[processor_name]

    def _execute(self):
        self.initialize()
        eval_object = UserAttemptResponseEvaluation.objects.get(id=self.evaluation_id)
        eval_object.ideal_response_details = self.ideal_response_details
        eval_object.save()
        return {}
    

class IELTSIdealResponseSaver(BaseIdealResponseSaver):

    def get_processor_name(self):
        return "IELTSIdealResponse"
    

class InterviewPrepIdealResponseSaver(BaseIdealResponseSaver):

    def get_processor_name(self):
        return "InterviewPrepIdealResponse"

class BaseDSAPracticeResponseSaver(BaseIdealResponseSaver):
    def initialize(self):
        self.question_attempt_id = self.root_arguments.get("question_attempt_id")
        self.assessment_attempt_id = self.root_arguments.get("assessment_attempt_id")
        
        # Fetch the UserEvalQuestionAttempt object
        self.eval_object = UserEvalQuestionAttempt.objects.get(id=self.question_attempt_id)
        self.eval_data = self.eval_object.eval_data
        
        # Fetch the AssessmentAttempt object
        self.assessment_attempt = AssessmentAttempt.objects.get(assessment_id=self.assessment_attempt_id)
        self.assessment_data = self.assessment_attempt.eval_data
    
    def update_eval_data(self, key, value):
        self.eval_data[key] = value
        self.eval_object.eval_data = self.eval_data
        self.eval_object.save()
    
        self.assessment_data[key] = value
        self.assessment_attempt.eval_data = self.assessment_data
        self.assessment_attempt.save()


class DSAResponseSaverEfficiency(BaseDSAPracticeResponseSaver):
    def _execute(self):
        self.initialize()
        efficiency = self.inputs["CodeEfficiencyProcessor"]["efficiency"]
        self.update_eval_data("code_efficiency_score", efficiency)
        return {}


class DSAResponseSaverQuality(BaseDSAPracticeResponseSaver):
    def _execute(self):
        self.initialize()
        quality = self.inputs["CodeQualityProcessor"]["CodeQuality"]
        self.update_eval_data("code_quality_score", quality)
        return {}


class DSAResponseSaverImprovement(BaseDSAPracticeResponseSaver):
    def _execute(self):
        self.initialize()
        improvement = self.inputs["CodeImprovementProcessor"]["Improvement"]
        self.update_eval_data("code_improvement_score", improvement)
        return {}


class DSAResponseSaverRevision(BaseDSAPracticeResponseSaver):
    def _execute(self):
        self.initialize()
        revision_topics = self.inputs["CodeRevisionTopicProcessor"]["RevisionTopics"]
        self.update_eval_data("code_revision_topics", revision_topics)
        return {}


class DSAResponseSaverSummary(BaseDSAPracticeResponseSaver):
    def _execute(self):
        self.initialize()
        summary = self.inputs["CodeSummaryProcessor"]["Summary"]
        self.update_eval_data("code_summary", summary)
        return {}


class DSAMarkAsCompleteSaver(BaseIdealResponseSaver):
    def initialize(self):
        self.question_attempt_id = self.root_arguments.get("question_attempt_id")

    def _execute(self):
        self.initialize()
        eval_object = UserEvalQuestionAttempt.objects.get(id=self.question_attempt_id)
        eval_object.status = UserEvalQuestionAttempt.Status.EVALUATED
        eval_object.save()
        return {}

