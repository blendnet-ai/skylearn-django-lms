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


class IELTSReportGenerator(EventProcessor):
    base_prompt = """You are a communication coach which rates the user on the following parameters and scale:

                1. Pronunciation: score on a scale of 100

                2. Fluency: score on a scale of 100

                3. Grammar: novice, beginner, intermediate, expert

                4. Coherence: unsatisfactory, good, excellent

                5. Vocabulary: user is given a CEFR level according to his speaking skills

                6. Filler words: BAD, AVERAGE, GOOD

                7. Pace: BAD, AVERAGE, GOOD



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

                6. Filler words: $filler_words_score

                7. Pace: $pace_score"""

    """
    test
    inputs={"Fluency":{"score":95,"fillerwords_percentage":50},
        "Pronunciation":{"score":50},
        "Grammar":{"score":5},
        "Vocab":{"score":"A1"},
        "Coherence":{"score":"Bad"},        
        "Pace":{"score":"Average"}
       }

    ig=IELTSReportGenerator(inputs=inputs,eventflow_id="temp",root_arguments={})
    ig._execute()
    """

    fillerwords_bands = [Band(0, 5, "GOOD"), Band(5, 15, "AVERAGE"), Band(15, 100.1, "BAD")]
    grammar_bands = [Band(0, 3.5, "Novice"), Band(4, 5.5, "Beginner"), Band(6, 7.5, "Intermediate"),
                     Band(8, 9, "Expert")]

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
        return IELTSReportGenerator.get_normalized_score(cls.fillerwords_bands, filler_words_percentage)

    @classmethod
    def generate_grammar_string_score_from_grammar_percentage(cls, grammar_score: int) -> str:
        return IELTSReportGenerator.get_normalized_score(cls.grammar_bands, grammar_score)

    def initialize(self):
        self.fluency_score = int(self.inputs["Fluency"]["score"])
        self.pronunciation_score = int(self.inputs["Pronunciation"]["score"])
        self.coherence_score = str(self.inputs["Coherence"]["score"])
        self.filler_words_percentage = self.inputs["Fluency"]["fillerwords_percentage"]
        self.filler_words_score: str = self.generate_fillerwords_string_score_from_fillerwords_percentage(
            self.filler_words_percentage)
        self.pace_score = str(self.inputs["Pace"]["score"])

        self.grammar_score:str = self.generate_grammar_string_score_from_grammar_percentage(
            int(self.inputs["Grammar"]["score"]))

        self.vocab_score = str(self.inputs["Vocab"]["score"]).replace("+", "")
        grammar_score_to_number_mapping = {"novice": 0.67, "beginner": 4.5, "intermediate": 6.5, "expert": 8.5}
        vocab_score_to_number_mapping = {"a1": 3.5, "a2": 4, "b1": 5, "b2": 6, "c1": 7.5, "c2": 8.5}

        normalized_fluency_score = self.fluency_score / 10
        normalized_pronunciation_score = self.pronunciation_score / 10
        normalized_grammar_score = grammar_score_to_number_mapping.get(self.grammar_score.lower())
        normalized_vocab_score = vocab_score_to_number_mapping.get(self.vocab_score.lower())
        # TODO - Calculate Normailzed Grammar Score
        self.log_info(
            f"Got normalized results - {normalized_fluency_score},{normalized_pronunciation_score}, {normalized_vocab_score},{self.grammar_score}")
        self.final_score = (normalized_fluency_score + normalized_pronunciation_score +
                            normalized_grammar_score+ normalized_vocab_score) / 4

        self.scores = {
            "pronunciation_score": self.pronunciation_score,
            "fluency_score": self.fluency_score,
            "grammar_score": self.grammar_score,
            "coherence_score": self.coherence_score,
            "vocab_score": self.vocab_score,
            "filler_words_score": self.filler_words_score,
            "pace_score": self.pace_score
        }

        #     {
        #     "pronunciation_score": 95,
        #     "fluency_score": 90,
        #     "grammar_score": "intermediate",
        #     "coherence_score": "good",
        #     "vocab_score": "b2",
        #     "filler_words_score": "GOOD",
        #     "pace_score": "Average"
        # }

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
