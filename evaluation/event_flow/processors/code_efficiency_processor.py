import logging
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService
import json

logger = logging.getLogger(__name__)


class CodeEfficiencyProcessor(EventProcessor):
    def initialize(self):
        self.question=self.root_arguments.get("question")
        self.solution=self.root_arguments.get("solution")
        self.chat_history=self.root_arguments.get("chat_history")
        self.system_message="""Your task is to assess user’s performance in a coding assessment. You will be given the assessment question and user’s response as input. Based on the inputs, review the user’s performance and provide:
                                1. Time complexity of the code
                                2. Space complexity of the code
                                3. Optimum Time complexity for the question
                                4. Optimum space complexity for the question. 
                                5. Quantitative score on a scale of 0-30 based on user response
                                
                                Output must strictly be in the below json format.
                                DON'T INCLUDE ANYTHING IN YOUR RESPONSE EXCEPT THE FOLLOWING JSON. 
                                IF THE SOLUTION IS NOT MATCHING THE QUESTION, MARK ALL SCORES AS NA AND GIVE REASONING IN REASONING KEY:
                                        {
                                        "reasoning": <The reasoning for giving all the scores you have given>
                                        "efficiency": {
                                        "Score": 0,
                                        "spacecomplexity": “”,
                                        "optimum_space_complexity":""
                                        "timecomplexity": “”,
                                        "optimumtimecomplexity": “”                                
                                        }
                                        }                                                             
                            }
                            """
        

    def _execute(self):
        self.initialize()
        llm = OpenAIService()
        
        messages = [
            {'role': 'system', 'content': self.system_message},
            {'role': 'user', 'content': f"""Assess the coding performance with question '{self.question}' and solution ####{self.solution}####."""}
        ]

        try:
            completion = llm.get_completion_from_messages(messages, llm_config_name="dsa_evaluation_gpt_1")
            logger.info(f'Code Efficiency Response from GPT : {completion}')
            output = json.loads(completion)
            # Check if the required structure is in the output
            if 'efficiency' not in output or 'Score' not in output['efficiency'] or 'spacecomplexity' not in output['efficiency'] or 'timecomplexity' not in output['efficiency'] or 'optimumtimecomplexity' not in output['efficiency']:
                raise ValueError('Missing required keys in the output: "efficiency", "Score", "spacecomplexity", "timecomplexity", or "optimumtimecomplexity"')
            
            return output
                    
        except json.JSONDecodeError:
            raise ValueError('The response from GPT is not valid JSON.')