import requests
import logging

from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.processors.expections import ProcessorException
from evaluation.vocab.vocab import evaluate_vocab
from evaluation.vocab.vocab_predictor import evaluate_vocab_level
from evaluation.event_flow.services.cefr_level_service import CEFRLevelService

logger = logging.getLogger(__name__)


class Vocab(EventProcessor):

    def get_fallback_result(self):
        return self._fallback_result

    def initialize(self):
        self.user_answer = self.root_arguments.get("text")
        if self.user_answer is None:
            self.transcript_url = self.inputs["SpeechToText"]["output_transcript_url"]
            response = requests.get(self.transcript_url, allow_redirects=True)
            if response.status_code != 200:
                raise Exception(
                    f"Error in reading transcript. Response code = {response.status_code}. Response - {response.content}"
                )
            self.user_answer = response.content.decode("utf-8")
        self.log_info(f"Extracted text - {self.user_answer}")

    def _execute(self):
        self.initialize()
        error = None
        try:
            vocab_level = CEFRLevelService().cefr_level(text=self.user_answer)
        except Exception as ex:
            self.log_warn(f"Error while evaluating vocab level e: {ex}")
            vocab_level = ""
            error = ex
        
        (
            num_unique_words,
            num_repeated_words,
            total_words,
            frequently_used_2000,
            percentage_frequently_used_2000,
            percentage_unique,
            rare_words,
            percentage_rare_words,
            level_counts,
            words_by_level,
            average_sentence_length,
            longest_sentence_length,
        ) = evaluate_vocab(self.user_answer)
        
        if error is not None:
            self._fallback_result = {
                "score": vocab_level,
                "vocal_insights": {
                    "num_unique_words": num_unique_words,
                    "num_repeated_words": num_repeated_words,
                    "total_words": total_words,
                    "frequently_used_2000": frequently_used_2000,
                    "frequently_used": round(percentage_frequently_used_2000),
                    "unique_words": round(percentage_unique),
                    "rare_words_count": rare_words,
                    "rare_words": round(percentage_rare_words),
                    "average_sentence_length": round(average_sentence_length),
                    "longest_sentence_length": longest_sentence_length,
                },
                "cefr_breakdown": level_counts,
                "words_by_level": words_by_level,
            }
            raise ProcessorException(message="Vocab error, in evaluating vocab level", original_error=error,
                                     extra_info={})

        return {
            "score": vocab_level,
            "vocal_insights": {
                "num_unique_words": num_unique_words,
                "num_repeated_words": num_repeated_words,
                "total_words": total_words,
                "frequently_used_2000": frequently_used_2000,
                "frequently_used": round(percentage_frequently_used_2000),
                "unique_words": round(percentage_unique),
                "rare_words_count": rare_words,
                "rare_words": round(percentage_rare_words),
                "average_sentence_length": round(average_sentence_length),
                "longest_sentence_length": longest_sentence_length,
            },
            "cefr_breakdown": level_counts,
            "words_by_level": words_by_level,
        }
