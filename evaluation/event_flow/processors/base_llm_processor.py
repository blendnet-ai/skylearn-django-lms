import json
import logging
from typing import Type, Dict, Any

from pydantic import BaseModel
from evaluation.event_flow.processors.base_event_processor import EventProcessor
from OpenAIService.repositories import LLMCommunicationWrapper, ValidPromptTemplates

logger = logging.getLogger(__name__)


class BaseLLMProcessor(EventProcessor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_template: ValidPromptTemplates = None
        self.response_format_class: Type[BaseModel] = None
        self.context: Dict[str, Any] = {}

    def initialize(self):
        pass

    def _execute(self) -> dict:
        self.initialize()

        if self.should_return_default_response():
            return self.format_response(self.response_format_class().dict())

        output = LLMCommunicationWrapper.get_response_without_chathistory(
            self.prompt_template,
            self.response_format_class,
            self.context,
            True,
        )

        logger.info(f"Output from LLM for {self.__class__.__name__}: {output}")

        return self.format_response(json.loads(output))

    def format_response(self, response: dict) -> dict:
        return response

    def should_return_default_response(self) -> bool:
        return False
