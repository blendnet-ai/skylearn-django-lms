import logging
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from evaluation.event_flow.services.llm_service.openai_service import OpenAIService
import json

logger = logging.getLogger(__name__)


class CodeSummaryProcessor(EventProcessor):
    def initialize(self):
        self.code_correctness = self.root_arguments.get("test_cases_score")
        self.code_efficiency = self.inputs["CodeEfficiencyProcessor"]["efficiency"]
        self.code_quality = self.inputs["CodeQualityProcessor"]["CodeQuality"]
        self.code_improvement = self.inputs["CodeImprovementProcessor"]["Improvement"]
        self.system_message= """Your task is to generate a qualitative summary for user based on the given scores. You will be provided with the scores for a coding assessment along with feedback. Based on the inputs, provide feedback on the following points:
                                1. Overall Summary
                                2. Strong Points
                                3. Areas of improvements
                                
                                Make sure that Output must be in first person.
                                Don't use terms like 'user's', 'candidate's', for addressing user who submitted the code. use terms like 'you' instead. 
                                For example = "Your code is correct. Overall it satisfies all conditions".
                                Output must be structured with each point clearly separated and explained. 
                                Output must strictly be in the following JSON format:
                                {
                                    "Summary":{
                                    "OverallSummary": “”,
                                    "StrongPoints":“”,
                                    "AreaOfImprovements:“”
                                    }

                                }"""
        
    def _execute(self):
        self.initialize()
        llm = OpenAIService()
        messages = [
            {'role': 'system', 'content': self.system_message},
            {'role': 'user', 'content': f'Provide feedback based on the scores and feedback: "code_correctness: {self.code_correctness}, code_efficiency: {self.code_efficiency}, code_quality: {self.code_quality}, code_improvement: {self.code_improvement}"'}
        ]

        try:
            completion = llm.get_completion_from_messages(messages, llm_config_name="dsa_evaluation_gpt_1")
            logger.info(f'Code Summary Response from GPT : {completion}')
            output = json.loads(completion)
            
            summary = output.get('Summary')
            required_keys = ['OverallSummary', 'StrongPoints', 'AreaOfImprovements']
            for key in required_keys:
                if key not in summary:
                    raise ValueError(f'Missing required key in output: {key}')
                
            return output
                    
        except json.JSONDecodeError:
            raise ValueError('The response from GPT is not valid JSON.')
        