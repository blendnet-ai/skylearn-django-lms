import difflib
import logging
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.processors.expections import ProcessorException

logger = logging.getLogger(__name__)


class Fluency(EventProcessor):
    """
    Fluency event processor
    """

    # Commented ones are optional, just tracking here
    # Update relevant schema ones freezed
    SCHEMA = {
        "Pitch": {
            "pitch_url": None,
            "observation": None,
        },
        "Pronunciation": {
            "score": 0,
        },
        "Pace": {
            "plot_url": None,
            "score": 0,
        },
        "AwkwardPauses": {
            "count": 0,
            "total_words_count": 0,
            "response": "",
            "original_text": "",
        },
        "FillerWords": {
            "count": 0,
            "response": "",
        },
    }

    def _validate(self, data, schema, heirarchy=""):
        if data is None and schema:
            self.log_warn(f"[Fluency] didn't found data for validation")
            return False

        for k, v in data.items():
            if k not in schema:
                self.log_warn(
                    f"[Fluency] while validating required data, found dependent data missing for key: {heirarchy}:{k}"
                )
                return False
            if isinstance(v, dict):
                return self._validate(v, schema.get(k), f"{heirarchy}:{k}")
            elif not data.get(k):
                self.log_warn(
                    f"[Fluency] while validating required data, found dependent data none for key: {heirarchy}:{k}"
                )
                return False

        return True

    def initialize(self):
        self.fluency_score = self.inputs["Pronunciation"].get("fluency_score", 0)
        self.pace_score = self.inputs["Pace"].get("score", 0)
        self.fillerwords_percentage = self._generate_fillerwords_percentage()

    def validate_input_data(self):
        return self._validate(self.inputs, self.SCHEMA)

    @staticmethod
    def _get_weighted_score(bands, score, default_score=0):
        weighted_score = default_score

        for st, ed, wscr in bands:
            if st <= score < ed:
                weighted_score = wscr
                break

        return weighted_score

    def _generate_fluency_score(self):
        # (start, end, score)
        pace_bands = [(140, 160, 10), (100, 140, 5), (160, 200, 5)]
        weighted_pace_score = self._get_weighted_score(pace_bands, self.pace_score)

        # (start, end, score)
        fillerwords_bands = [(0, 5, 10), (5, 15, 5)]
        weighted_fillerwords_score = self._get_weighted_score(
            fillerwords_bands, self.fillerwords_percentage
        )

        computed_fluency_score = 0.8 * self.fluency_score
        + weighted_pace_score
        + weighted_fillerwords_score

        self.log_info(
            f"f_score: {computed_fluency_score}, p_score: {weighted_pace_score}, fw_score: {weighted_fillerwords_score}"
        )
        return computed_fluency_score

    def _generate_fillerwords_percentage(self):
        # % FILLER WORDS = (Number of filler words + number of Awkward pauses)/ TOTAL WORDS
        filler_words_count = self.inputs["FillerWords"].get("count", 0)
        awkward_pauses_count = self.inputs["AwkwardPauses"].get("count", 0)
        total_words_count = self.inputs["AwkwardPauses"].get("total_words_count", 1)

        return ((filler_words_count + awkward_pauses_count) * 100) / total_words_count
    
    def _highlight_missing_words(self, original_text, modified_text, filler_words):

        og_words = original_text.strip().split() # contains awkward pauses
        mod_words = modified_text.strip().split() # fillerwords removed

        if not modified_text:
            self.log_warn("[fluency] Fillerword response was missing, hence not highlighting.")
            return original_text

        d = difflib.Differ()
        diff = list(d.compare(mod_words, og_words))

        highlighted_words = []
        for line in diff:
            word = line[2:]
            if line.startswith('  '):
                highlighted_words.append(word)
            elif line.startswith('+ '):
                clean_word = "".join(filter(str.isalnum, word))
                if clean_word in filler_words:
                    word = f"**{word}**"
                elif word in filler_words:
                    word = f"**{word}**"
                highlighted_words.append(word)
        
        return " ".join(highlighted_words)

    def _execute(self):
        # Raise exception, break flow
        if not self.validate_input_data():
            self.log_warn("[Fluency] input data is malformed")

        self.initialize()
        
        try:
            marked_transcript = self._highlight_missing_words(
                self.inputs["AwkwardPauses"]["response"], self.inputs["FillerWords"]["response"],
                self.inputs["FillerWords"].get("fillerwords", []))
        except Exception as ex:
            self.log_warn(f"[fluency] error while highlighing transcript, err: {ex}")
            marked_transcript = self.inputs["AwkwardPauses"]["response"]

        score = self._generate_fluency_score()
            
        # TODO:
        # 1. created nested dictionary schema like "pitch" -> "url"
        # 2. rename keys to relevant names
        # 3. remove hardcodings
        res = {
            "score": score,
            "pitch_image_url": self.inputs["Pitch"].get("pitch_url"),
            "pace_image_url": self.inputs["Pace"].get("plot_url"),
            "transcript": marked_transcript,
            "original_text": self.inputs["AwkwardPauses"]["original_text"],
            "fillerwords_percentage": self.fillerwords_percentage,
            "pace_score": self.pace_score,
            "fluency_score": self.fluency_score,
            "percentage_mispronounced": self.inputs["Pronunciation"].get("percentage_mispronounced", 0),
            "pitch_summary": self.inputs["Pitch"].get("observation"),
        }
        return res
