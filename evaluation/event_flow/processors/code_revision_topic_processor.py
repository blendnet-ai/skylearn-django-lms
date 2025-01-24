import logging

from openai import BaseModel
from OpenAIService.repositories import ValidPromptTemplates
from evaluation.event_flow.processors.base_llm_processor import (
    BaseLLMProcessor,
)

logger = logging.getLogger(__name__)


class Response(BaseModel):
    RevisionTopics: str = "No solution was submitted."


class CodeRevisionTopicProcessor(BaseLLMProcessor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_template = ValidPromptTemplates.CODE_REVISION_TOPIC_PROCESSOR
        self.response_format_class = Response

    def initialize(self):
        super().initialize()
        self.context["solution"] = self.root_arguments.get("solution")
        self.context["question"] = self.root_arguments.get("question")

    def should_return_default_response(self) -> bool:
        return self.context["solution"] is None or self.context["solution"] == ""
