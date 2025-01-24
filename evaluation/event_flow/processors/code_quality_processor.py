import logging
from evaluation.event_flow.processors.base_llm_processor import BaseLLMProcessor
from OpenAIService.repositories import ValidPromptTemplates
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Response(BaseModel):
    class FeedbackModel(BaseModel):
        CodeReadabilityBestPractices: str = "NA"
        VariableNaming: str = "NA"
        CodeStructure: str = "NA"
        UsageOfComments: str = "NA"

    Score: int = 0
    Feedback: FeedbackModel = FeedbackModel()


class CodeQualityProcessor(BaseLLMProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_template = ValidPromptTemplates.CODE_QUALITY_PROCESSOR
        self.response_format_class = Response

    def initialize(self):
        super().initialize()
        self.context["solution"] = self.root_arguments.get("solution")
        self.context["question"] = self.root_arguments.get("question")

    def format_response(self, response: dict) -> dict:
        return {"CodeQuality": response}

    def should_return_default_response(self) -> bool:
        return self.context["solution"] is None or self.context["solution"] == ""
