import dataclasses
import logging
import requests
import json
import os

from evaluation.event_flow.helpers.sentiment import evaluate_sentiment
from evaluation.event_flow.processors.base_event_processor import EventProcessor

from evaluation.event_flow.services.llm_service.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class Sentiment(EventProcessor):
    @dataclasses.dataclass
    class SentimentLLMResponse:
        feedback: str
        confidence_rating: str  # HIGH/MODERATE/LOW

    def get_feedback_and_confidence_rating_using_llm(self, user_answer: str, sentiment_rating: str,
                                                     llm_object) -> SentimentLLMResponse:

        system_message = f"""
        You are a communication coach training students for professional interviews. You have to give critical yet 
        motivating feedback to user on his overall speech sentiment and confidence.
 
        There are two criteria - confidence and sentiment, each rated on a scale of 3 as follows:
         
        1. confidence - high, moderate, low
        2. sentiment - positive, negative, neutral
         
        Your task is to
        1.  give a confidence rating as - HIGH/MODERATE/LOW based on user response.
         
        user response is -
        {llm_object.get_delimiter()}
        {user_answer}
        {llm_object.get_delimiter()}
         
        2. give a feedback in 50 words based on user's confidence and sentiment rating.
         
        sentiment rating is {sentiment_rating}
                  
        output should be a JSON dictionary that has a confidence rating, 50-word feedback with following keys
        {{confidence_rating:"",feedback,""}}    
        
        The output must always be a JSON dictionary and Nothing else.    
        """

        messages = [
            {'role': 'system', 'content': system_message},
        ]

        response = llm_object.get_completion_from_messages(messages)
        try:
            response_dict = json.loads(response)
            return self.SentimentLLMResponse(feedback=response_dict["feedback"],
                                      confidence_rating=response_dict["confidence_rating"])
        except Exception as e:
            self.log_error(f"Got exception while decoding LLM response -{e} .LLM RESPONSE was \n{response}.\n")
            return self.SentimentLLMResponse(feedback="Could not load feedback.", confidence_rating="MODERATE")


    def initialize(self):
        self.text = self.root_arguments.get("text")
        if self.text is None:
            self.transcript_url = self.inputs["SpeechToText"]["output_transcript_url"]
            response = requests.get(self.transcript_url, allow_redirects=True)
            if response.status_code != 200:
                raise Exception(
                    f"Error in reading transcript. Response code = {response.status_code}. Response - {response.content}")
            self.text = response.content.decode('utf-8')

    def _execute(self):
        # self.initialize()
        # llm_object = OpenAIService()
        # sentiment_response = evaluate_sentiment(text=self.text)
        # sentiment_llm_response = self.get_feedback_and_confidence_rating_using_llm(self.text,
        #                                                                            sentiment_response.sentiment_rating,
        #                                                                            llm_object)
        return {
  "sentiment": "positive",
  "confidence": "MODERATE",
  "overall_remark": "Your overall speech was good, but there were moments where your confidence seemed to waver. Try to maintain a consistent level of confidence throughout your speech. Your positive sentiment was evident and it added to the overall impact of your speech. Keep up the good work!"
}

