import dataclasses
import requests
import json

from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.processors.expections import ProcessorException
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService


@dataclasses.dataclass
class IdealResponseLLMResult:
    ideal_response: str


class BaseIdealResponse(EventProcessor):
    """
    Processor to generate ideal response for a given question using llm
    """
    
    def get_fallback_result(self):
        return self._fallback_result

    def get_system_message(self) -> str:
        raise NotImplementedError

    def _get_ideal_response_from_llm(self) -> IdealResponseLLMResult:
        system_message = self.get_system_message()

        messages = [
            {"role": "system", "content": system_message},
        ]

        response = self.openai_service.get_completion_from_messages(messages)
        try:
            response_dict = json.loads(response, strict=False)
            return IdealResponseLLMResult(
                ideal_response=response_dict["ideal_response"]
            )
        except (json.JSONDecodeError, KeyError) as e:
            err_msg = f"While parsing response from llm, some of the key were missing, err: {e}. LLM Response was {response}"
            self.log_error(err_msg)
            self._fallback_result = {
                "ideal_response": None,
                "question_text": self.question,
                "user_response": self.user_answer,
            }
            raise ProcessorException(
                message=err_msg,
                original_error=e,
                extra_info={},
            )

    def initialize(self):
        self.transcript_url = self.inputs["SpeechToText"]["output_transcript_url"]
        response = requests.get(self.transcript_url, allow_redirects=True)
        if response.status_code != 200:
            raise Exception(
                f"Error in reading transcript. Response code = {response.status_code}. Response - {response.content}"
            )
        self.user_answer = response.content.decode("utf-8")
        self.question = self.root_arguments["question"]

    def _execute(self):
        self.initialize()
        self.openai_service = OpenAIService()

        llm_ideal_response = self._get_ideal_response_from_llm()

        return {
            "ideal_response": llm_ideal_response.ideal_response,
            "question_text": self.question,
            "user_response": self.user_answer,
        }


class IELTSIdealResponse(BaseIdealResponse):
    """
    Processor to generate ideal response for a given ielts question using llm
    """

    def get_system_message(self) -> str:
        msg = f"""
        You are a communication coach training students for IELTS exam. You have to generate an ideal answer for the question by using the points in user's answer.
        Make sure the answer is appropriate for a formal setting, grammatically correct and has a positive overall sentiment. 
        You can include additional relevant points in the answer that the user might have missed.

        Question: {self.question}

        User's answer - 
        {self.openai_service.get_delimiter()}
        {self.user_answer}
        {self.openai_service.get_delimiter()}
        
        Output should be a JSON with a key ideal_response
        """
        return msg


class InterviewPrepIdealResponse(BaseIdealResponse):
    """
    Processor to generate ideal response for a given interview prep question using llm
    """

    def get_system_message(self) -> str:
        msg = f"""
        You are a communication coach training students for professional interviews. You have to generate an ideal answer for the question by using the points in user's answer.
        Make sure the answer is appropriate for a formal setting, grammatically correct and has a positive overall sentiment. 

        Question: {self.question}

        User's answer - 
        {self.openai_service.get_delimiter()}
        {self.user_answer}
        {self.openai_service.get_delimiter()}
        
        Output should be a JSON with a key ideal_response
        """
        return msg
