from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from django.conf import settings
import dataclasses


@dataclasses.dataclass
class SentimentResponse:
    sentiment_rating: str  # postive/neutral/negative


def evaluate_sentiment(text: str) -> SentimentResponse:
    ta_credential = AzureKeyCredential(settings.AZURE_TEXT_ANALYTICS_CLIENT_KEY)  # os.environ["language_key"]
    client = TextAnalyticsClient(endpoint=settings.AZURE_TEXT_ANALYTICS_CLIENT_ENDPOINT,
                                 credential=ta_credential)  # os.environ["language_endpoint"]
    result = client.analyze_sentiment([text])
    doc_result = [doc for doc in result if not doc.is_error]

    # positive_reviews = [doc for doc in doc_result if doc.sentiment == "positive"]
    # negative_reviews = [doc for doc in doc_result if doc.sentiment == "negative"]

    # positive_mined_opinions = []
    # mixed_mined_opinions = []
    # negative_mined_opinions = []
    #

    if len(doc_result):
        sentiment_response = SentimentResponse(sentiment_rating=doc_result[0].sentiment)
        if sentiment_response.sentiment_rating == 'mixed':
            positive_score = doc_result[0].confidence_scores.positive
            negative_score = doc_result[0].confidence_scores.negative
            if positive_score - negative_score > 0.2:
                return SentimentResponse(sentiment_rating='positive')
            elif negative_score - positive_score > 0.2:
                return SentimentResponse(sentiment_rating='negative')
            else:
                return SentimentResponse(sentiment_rating='neutral')
        # response["Overall scores"] =  {"positive":document.confidence_scores.positive,
        #                                     "neutral":document.confidence_scores.neutral,
        #                                     "negative":document.confidence_scores.negative}
        # for sentence in document.sentences:
        #     # response.append({"Sentence": sentence.text, "Sentiment": sentence.sentiment, "Sentence score": {"Positive":sentence.confidence_scores.positive, "Neutral":sentence.confidence_scores.neutral,"Negative": sentence.confidence_scores.negative}})
        #     for mined_opinion in sentence.mined_opinions:
        #         target = mined_opinion.target
        #         print("......'{}' target '{}'".format(target.sentiment, target.text))
        #         print("......Target score:\n......Positive={0:.2f}\n......Negative={1:.2f}\n".format(
        #             target.confidence_scores.positive,
        #             target.confidence_scores.negative,
        #         ))
        #         for assessment in mined_opinion.assessments:
        #             print("......'{}' assessment '{}'".format(assessment.sentiment, assessment.text))
        #             print("......Assessment score:\n......Positive={0:.2f}\n......Negative={1:.2f}\n".format(
        #                 assessment.confidence_scores.positive,
        #                 assessment.confidence_scores.negative,
        #             ))
        return sentiment_response
