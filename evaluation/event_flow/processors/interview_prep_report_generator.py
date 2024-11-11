import dataclasses
import json
import logging
import typing
from string import Template
from common.utilities import round_to_pt5

from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class Band:
    start: typing.Union[float | int]
    end: typing.Union[float | int]
    result: typing.Union[str | float | int]


class InteviewPrepReportGenerator(EventProcessor):
    base_prompt = """You are a communication coach which rates the user on the following parameters and scale:

                1. Pronunciation: score on a scale of 100

                2. Fluency: score on a scale of 100

                3. Grammar: score on a scale of 10

                4. Coherence: unsatisfactory, good, excellent

                5. Vocabulary: user is given a CEFR level according to his speaking skills

                6. Emotion: score on a scale of 10

                7. Filler words: BAD, AVERAGE, GOOD

                8. Pace: BAD, AVERAGE, GOOD



                You have to give the user a one word label and a 50 words performance summary depending upon his score on the above parameters.



                Output two things in a JSON format with mentioned keys:

                1. title: One word summary title which shows user proficiency.

                2. summary: 50 words performance summary. The language of summary should be addressing to the user himself.



                the score of the user is given below:



                1. Pronunciation: $pronunciation_score/100

                2. Fluency: $fluency_score/100

                3. Grammar: $grammar_score

                4. Coherence: $coherence_score

                5. Vocabulary: $vocab_score

                6. Emotion: $sentiment_score

                7. Filler words: $filler_words_score

                8. Pace: $pace_score"""

    """
    test
    inputs={"Fluency":{"score":95,"fillerwords_percentage":50},
        "Pronunciation":{"score":50},
        "InterviewPrepGrammar":{"score":5},
        "Vocab":{"score":"A1"},
        "Coherence":{"score":"Bad","Completeness":"no","Relevence":"low","Logical": "medium"},        
        "Pace":{"score":"Average"},
        "Sentiment":{"confidence":"Moderate","sentiment":"neutral"}
       }

    ig=InteviewPrepReportGenerator(inputs=inputs,eventflow_id="temp",root_arguments={})
    ig._execute()
    """

    fillerwords_bands = [Band(0, 5, "GOOD"), Band(5, 15, "AVERAGE"), Band(15, 100.1, "BAD")]

    @classmethod
    def get_normalized_score(cls, bands: typing.List[Band], score: typing.Union[int | float]):
        calculated_score = None
        for band in bands:
            if band.start <= score < band.end:
                calculated_score = band.result
                break
        if calculated_score is None:
            raise ValueError(f"Couldn't place the score {score} in bands - {bands}")

        return calculated_score

    @classmethod
    def generate_fillerwords_string_score_from_fillerwords_percentage(cls, filler_words_percentage: float) -> str:
        return InteviewPrepReportGenerator.get_normalized_score(cls.fillerwords_bands, filler_words_percentage)

    def initialize(self):
        self.fluency_score = int(self.inputs["Fluency"]["score"])
        self.pronunciation_score = int(self.inputs["Pronunciation"]["score"])
        self.coherence_score = str(self.inputs["Coherence"]["score"])
        self.grammar_score = int(self.inputs["InterviewPrepGrammar"]["score"])
        self.filler_words_percentage = self.inputs["Fluency"]["fillerwords_percentage"]
        self.filler_words_score: str = self.generate_fillerwords_string_score_from_fillerwords_percentage(
            self.filler_words_percentage)
        self.pace_score = str(self.inputs["Pace"]["score"])
        self.vocab_score = str(self.inputs["Vocab"]["score"]).replace("+", "")

        self.coherence_completeness = str(self.inputs["Coherence"]["response"]["Completeness"])
        self.coherence_relevence = str(self.inputs["Coherence"]["response"]["Relevance"])
        self.coherence_logical = str(self.inputs["Coherence"]["response"]["Logical"])
        
        self.sentiment_confidence = str(self.inputs["Sentiment"]["confidence"])
        self.sentiment_sentiment = str(self.inputs["Sentiment"]["sentiment"])
        
        vocab_score_to_number_mapping = {"a1": 1, "a2": 3, "b1": 5, "b2": 7, "c1": 8.5, "c2": 9.5}

        coherence_completeness_to_number_mapping = {"yes": 2, "no": 1}
        coherence_relevance_to_number_mapping = {"high": 6, "medium": 3, "low": 1}
        coherence_logical_to_number_mapping = {"high": 2, "medium": 1, "low": 0}

        sentiment_confidence_to_number_mapping = {"high": 8, "moderate": 4, "low": 2}
        sentiment_sentiment_to_number_mapping = {"positive": 2, "neutral": 1, "negative": 0}

        normalized_fluency_score = self.fluency_score / 10
        normalized_pronunciation_score = self.pronunciation_score / 10
        normalized_vocab_score = vocab_score_to_number_mapping.get(self.vocab_score.lower())

        normalized_coherence_score = sum([
            coherence_completeness_to_number_mapping.get(self.coherence_completeness.lower()),
            coherence_relevance_to_number_mapping.get(self.coherence_relevence.lower()),
            coherence_logical_to_number_mapping.get(self.coherence_logical.lower())
        ])

        normalized_sentiment_score = sum([
            sentiment_confidence_to_number_mapping.get(self.sentiment_confidence.lower()),
            sentiment_sentiment_to_number_mapping.get(self.sentiment_sentiment.lower())
        ])

        self.log_info(
            f"Got normalized results - "
            f"Pronunciation: {normalized_pronunciation_score}, "
            f"Fluency: {normalized_fluency_score}, "
            f"Coherence: {normalized_coherence_score}, "
            f"Vocabulary: {normalized_vocab_score}, "
            f"Sentiment: {normalized_sentiment_score}"
        )

        self.final_score = (
            normalized_pronunciation_score +
            normalized_fluency_score +
            self.grammar_score +
            normalized_coherence_score +
            normalized_vocab_score +
            normalized_sentiment_score
        ) / 6

        self.log_info(f"Final score - {self.final_score}")

        self.scores = {
            "pronunciation_score": self.pronunciation_score,
            "fluency_score": self.fluency_score,
            "grammar_score": self.grammar_score,
            "coherence_score": self.coherence_score,
            "vocab_score": self.vocab_score,
            "sentiment_score": normalized_coherence_score,
            "filler_words_score": self.filler_words_score,
            "pace_score": self.pace_score
        }

    def _execute(self):
        self.initialize()
        src = Template(self.base_prompt)
        result = src.substitute(self.scores)
        llm = OpenAIService()
        messages = [
            {'role': 'system', 'content': result},
        ]
        response = json.loads(llm.get_completion_from_messages(messages))
        summary = response.get("summary")
        title = response.get("title")
        return {"summary": summary, "score_title": title, "score": round_to_pt5(self.final_score)}
