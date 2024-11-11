from evaluation.event_flow.processors.base_event_processor import EventProcessor

class MockBehaviourFinalScore(EventProcessor):

    def initialize(self):
        self.fluency_score = int(self.inputs["Fluency"]["score"])

        self.coherence_score = str(self.inputs["Coherence"]["score"])

        self.coherence_completeness = str(self.inputs["Coherence"]["response"]["Completeness"])
        self.coherence_relevence = str(self.inputs["Coherence"]["response"]["Relevance"])
        self.coherence_logical = str(self.inputs["Coherence"]["response"]["Logical"])
        
        self.sentiment_confidence = str(self.inputs["Sentiment"]["confidence"])
        self.sentiment_sentiment = str(self.inputs["Sentiment"]["sentiment"])


    def _execute(self):
        self.initialize()

        sentiment_confidence_to_number_mapping = {"high": 8, "moderate": 4, "low": 2}
        sentiment_sentiment_to_number_mapping = {"positive": 2, "neutral": 1, "negative": 0}

        coherence_completeness_to_number_mapping = {"yes": 2, "no": 1}
        coherence_relevance_to_number_mapping = {"high": 6, "medium": 3, "low": 1}
        coherence_logical_to_number_mapping = {"high": 2, "medium": 1, "low": 0}

      
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



        return { "coherence": normalized_coherence_score, "fluency": normalized_fluency_score, "sentiment": normalized_sentiment_score}
