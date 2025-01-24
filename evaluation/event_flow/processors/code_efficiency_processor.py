import logging

from openai import BaseModel

from OpenAIService.repositories import (
    ValidPromptTemplates,
)

from evaluation.event_flow.processors.base_llm_processor import BaseLLMProcessor

logger = logging.getLogger(__name__)


class Response(BaseModel):
    class Efficiency(BaseModel):
        Score: int = 0
        spacecomplexity: str = "NA"
        optimum_space_complexity: str = "NA"
        timecomplexity: str = "NA"
        optimumtimecomplexity: str = "NA"

    reasoning: str = "No solution was submitted."
    efficiency: Efficiency = Efficiency()


class CodeEfficiencyProcessor(BaseLLMProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_template = ValidPromptTemplates.CODE_EFFICIENCY_PROCESSOR
        self.response_format_class = Response

    def initialize(self):
        super().initialize()
        self.context["solution"] = self.root_arguments.get("solution")
        self.context["question"] = self.root_arguments.get("question")

    def should_return_default_response(self) -> bool:
        return self.context["solution"] is None or self.context["solution"] == ""
