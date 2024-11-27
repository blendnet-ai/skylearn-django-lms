import logging
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService
import json

logger = logging.getLogger(__name__)


class CodeImprovementProcessor(EventProcessor):
    def initialize(self):
        self.question=self.root_arguments.get("question")
        self.solution=self.root_arguments.get("solution")
        self.chat_history=self.root_arguments.get("chat_history")
        self.system_message="""Your task is to assess user’s performance in a coding assessment. You will be given the assessment question, user’s response and user’s conversation history with AI bot as input. Based on the inputs, review the user’s performance and provide:
                                1. Qualitative feedback on user’s areas of improvement and how well did the user incorporate the feedback given by AI during the assessment. Make sure that feedback is in first person format.
                                2. A quantitative score on a scale of 0 to 10 based on user’s performance
                                Output must strictly be in the below json format:
                                {
                                "Improvement": {
                                "Score": 0,
                                "Feedback": “”
                                }
                            }"""
        

    def _execute(self):
        self.initialize()
        llm = OpenAIService()

        messages = [
            {'role': 'system', 'content': self.system_message},
            {'role': 'user', 'content': f'Assess the coding performance with question "{self.question}", solution "{self.solution}" and conversation history "{self.chat_history}".'}
        ]

        try:
            completion = llm.get_completion_from_messages(messages, llm_config_name="dsa_evaluation_gpt_1")
            logger.info(f'Code Improvement Response from GPT : {completion}')
            output = json.loads(completion)  #{\n"Improvement": {\n"Score": 0,\n"Feedback": “”\n}\n}
            
            # Check if the required structure is in the output
            if 'Improvement' not in output or 'Score' not in output['Improvement'] or 'Feedback' not in output['Improvement']:
                raise ValueError('Missing required keys in the output: "Improvement", "Score", or "Feedback"')
            
            return output
                    
        except json.JSONDecodeError:
            raise ValueError('The response from GPT is not valid JSON.')
        
