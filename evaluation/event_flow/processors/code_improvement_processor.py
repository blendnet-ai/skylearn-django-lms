from evaluation.event_flow.processors.base_llm_processor import BaseLLMProcessor
from OpenAIService.repositories import ValidPromptTemplates
from pydantic import BaseModel


class Response(BaseModel):
    Score: int = 0
    Feedback: str = "No solution was submitted."


class CodeImprovementProcessor(BaseLLMProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_template = ValidPromptTemplates.CODE_IMPROVEMENT_PROCESSOR
        self.response_format_class = Response

    def initialize(self):
        super().initialize()
        self.context["solution"] = self.root_arguments.get("solution")
        self.context["question"] = self.root_arguments.get("question")
        self.context["chat_history"] = self.root_arguments.get("chat_history")

    def format_response(self, response: dict) -> dict:
        return {"Improvement": response}

    def should_return_default_response(self) -> bool:
        return self.context["solution"] is None or self.context["solution"] == ""
