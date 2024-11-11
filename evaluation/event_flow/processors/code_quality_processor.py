import logging
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService
import json

logger = logging.getLogger(__name__)


class CodeQualityProcessor(EventProcessor):
    def initialize(self):
        self.question=self.root_arguments.get("question")
        self.solution=self.root_arguments.get("solution")
        self.system_message="""Your task is to assess coding assignments of students. You will be provided with the assignment question and user’s solution. You will provide:
                                1. A quantitative score on a scale of 0 to 20 based on code quality
                                2. qualitative feedback on the assignment based on readability and best practices,  areas for improvement like variable naming, code structure, and usage of comments.  Make sure that feedback is in first person format.

                                IF EVERYTHING LOOKS GOOD AWARD USER WITH FULL SCORE.
                                Output must strictly be in the following JSON format:

                                {
                                "CodeQuality": {
                                "Score": 0,
                                "Feedback": {
                                    "CodeReadabilityBestPractices": "",
                                    "VariableNaming": "",
                                    "CodeStructure": "",
                                    "UsageOfComments": ""
                                }
                                }
                                }"""
        
    def _execute(self):
        self.initialize()
        llm = OpenAIService()
        
        messages = [
            {'role': 'system', 'content': self.system_message},
            {'role': 'user', 'content': f'Assess the coding assignment with question "{self.question}" and solution "{self.solution}".'}
        ]

        try:
            completion = llm.get_completion_from_messages(messages, llm_config_name="dsa_evaluation_gpt_2")
            logger.info(f'Code Quality Response from GPT : {completion}')
            output = json.loads(completion)
            
            # Check if the required structure is in the output
            if 'CodeQuality' not in output or 'Score' not in output['CodeQuality'] or 'Feedback' not in output['CodeQuality'] or 'CodeReadabilityBestPractices' not in output['CodeQuality']['Feedback'] or 'VariableNaming' not in output['CodeQuality']['Feedback'] or 'CodeStructure' not in output['CodeQuality']['Feedback'] or 'UsageOfComments' not in output['CodeQuality']['Feedback']:
                raise ValueError('Missing required keys in the output: "CodeQuality", "Score", "Feedback"')
            
            return output
                    
        except json.JSONDecodeError:
            raise ValueError('The response from GPT is not valid JSON.')
