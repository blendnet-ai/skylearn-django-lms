import logging
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService
import json

logger = logging.getLogger(__name__)


class CodeRevisionTopicProcessor(EventProcessor):
    def initialize(self):
        self.question=self.root_arguments.get("question")
        self.solution=self.root_arguments.get("solution")
        self.system_message= """Your task is to generate a qualitative summary based on the given scores. You will be provided with the question, user's response, user's scores for a coding assessment along with feedback. Act like a teaching assistant for the student and give feedback in first person. Based on the inputs, provide feedback on the following points:
                                1.List of DSA Topics to revise in the context of the question and user's solution. output a list in markdown format.
                                
                                Make sure that feedback is strictly in first person format.
                                Output must be structured with each point clearly separated and explained.
                                Output must strictly be in the following JSON format:
                                {
                                    "RevisionTopics":“”
                                }"""
        
    def _execute(self):
        self.initialize()
        llm = OpenAIService()
        messages = [
            {'role': 'system', 'content': self.system_message},
           {'role': 'user', 'content': f'Provided question, user\'s solution: "question":{self.question}, "solution":{self.solution}'}
        ]

        try:
            completion = llm.get_completion_from_messages(messages, llm_config_name="dsa_evaluation_gpt_2")
            logger.info(f'Code Revision Response from GPT : {completion}')
            output = json.loads(completion)
            
            required_keys = ['RevisionTopics']
            for key in required_keys:
                if key not in output:
                    raise ValueError(f'Missing required key in output: {key}')
                
            return output
                    
        except json.JSONDecodeError:
            raise ValueError('The response from GPT is not valid JSON.')
        