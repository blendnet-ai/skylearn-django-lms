from evaluation.event_flow.processors.base_event_processor import EventProcessor

class SpeakingFinalScore(EventProcessor):

    def initialize(self):
        self.fluency_score = int(self.inputs["Fluency"]["score"])
        self.pronunciation_score = int(self.inputs["Pronunciation"]["score"])
        self.coherence_score = str(self.inputs["Coherence"]["score"])
        self.grammar_score = int(self.inputs["InterviewPrepGrammar"]["score"])
        self.vocab_score = str(self.inputs["Vocab"]["score"]).replace("+", "")

        self.coherence_completeness = str(self.inputs["Coherence"]["response"]["Completeness"])
        self.coherence_relevence = str(self.inputs["Coherence"]["response"]["Relevance"])
        self.coherence_logical = str(self.inputs["Coherence"]["response"]["Logical"])
        
        self.sentiment_confidence = str(self.inputs["Sentiment"]["confidence"])
        self.sentiment_sentiment = str(self.inputs["Sentiment"]["sentiment"])


    def _execute(self):
        self.initialize()
        vocab_score_to_number_mapping = {"a1": 1, "a2": 3, "b1": 5, "b2": 7, "c1": 8.5, "c2": 9.5}

        sentiment_confidence_to_number_mapping = {"high": 8, "moderate": 4, "low": 2}
        sentiment_sentiment_to_number_mapping = {"positive": 2, "neutral": 1, "negative": 0}

        coherence_completeness_to_number_mapping = {"yes": 2, "no": 1}
        coherence_relevance_to_number_mapping = {"high": 6, "medium": 3, "low": 1}
        coherence_logical_to_number_mapping = {"high": 2, "medium": 1, "low": 0}

        normalized_vocab_score = vocab_score_to_number_mapping.get(self.vocab_score.lower())*10 or 0

        normalized_pronunciation_score = self.pronunciation_score 
        normalized_fluency_score = self.fluency_score 

        normalized_coherence_score = sum([
            coherence_completeness_to_number_mapping.get(self.coherence_completeness.lower()),
            coherence_relevance_to_number_mapping.get(self.coherence_relevence.lower()),
            coherence_logical_to_number_mapping.get(self.coherence_logical.lower())
        ])*10

        normalized_sentiment_score = sum([
            sentiment_confidence_to_number_mapping.get(self.sentiment_confidence.lower()),
            sentiment_sentiment_to_number_mapping.get(self.sentiment_sentiment.lower())
        ])*10
        
        normalized_grammar_score = self.grammar_score*10

        final_score = round((
            int(normalized_pronunciation_score) +
            int(normalized_fluency_score) +
            int(normalized_grammar_score) +
            int(normalized_coherence_score) +
            int(normalized_vocab_score) +
            int(normalized_sentiment_score)
        ) / 6, 1)

        return {"final_score": final_score, "grammar": normalized_grammar_score, "vocab": normalized_vocab_score, "coherence": normalized_coherence_score, "fluency": normalized_fluency_score, "pronunciation": normalized_pronunciation_score, "sentiment": normalized_sentiment_score}
