import logging
import json
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService

logger = logging.getLogger(__name__)

class LSRW_Summary_Processor():
    def __init__(self,eval_data):
        self.eval_data = eval_data
        
    def initialize(self):
        self.system_message = """
        Your task is to generate an overall summary for a LSRW Test. You will be given the evaluation data as input. Based on the inputs, provide:
            1. An Overall summary combining all provided user responses and their ideal responses.
        
        Make sure that Output must be in first person.
        Don't use terms like 'user's', 'candidate's', for addressing user who submitted the code. use terms like 'you' instead. 
        For example = "Your code is correct. Overall it satisfies all conditions".
        
        Output must strictly be in the following JSON format:
        {
            "overall_summary": <overall summary based on the user responses and ideal responses>,
        }
        """

    def _execute(self):
        self.initialize()
        self.openai_service = OpenAIService()
        
        messages = [
            {'role': 'system', 'content': self.system_message},
            {'role': 'user', 'content': f"Evaluate the following data: {json.dumps(self.eval_data)}"}
        ]

        try:
            completion = self.openai_service.get_completion_from_messages(messages)
            logger.info(f'Response from GPT: {completion}')
            output = json.loads(completion)
            # Check if the required structure is in the output
            if 'overall_summary' not in output:
                raise ValueError('Missing required keys in the output: overall_summary')
            
            return output

        except json.JSONDecodeError:
            raise ValueError('The response from GPT is not valid JSON.')
        except Exception as e:
            logger.error(f'Error in generating response: {e}')

