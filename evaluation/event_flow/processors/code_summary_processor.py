import logging

from openai import BaseModel

from OpenAIService.repositories import ValidPromptTemplates
from evaluation.event_flow.processors.base_llm_processor import (
    BaseLLMProcessor,
)

logger = logging.getLogger(__name__)


class Response(BaseModel):
    OverallSummary: str = "NA"
    StrongPoints: str = "NA"
    AreaOfImprovements: str = "NA"


class CodeSummaryProcessor(BaseLLMProcessor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_template = ValidPromptTemplates.CODE_SUMMARY_PROCESSOR
        self.response_format_class = Response

    def initialize(self):
        super().initialize()
        self.context["code_correctness"] = self.root_arguments.get("test_cases_score")
        self.context["code_efficiency"] = self.inputs["CodeEfficiencyProcessor"][
            "efficiency"
        ]
        self.context["code_quality"] = self.inputs["CodeQualityProcessor"][
            "CodeQuality"
        ]
        self.context["code_improvement"] = self.inputs["CodeImprovementProcessor"][
            "Improvement"
        ]

    def format_response(self, response: dict) -> dict:
        return {"Summary": response}


class ApproachResponse(BaseModel):
    OverallSummary: str = "NA"


class ApproachCodeSummaryProcessor(BaseLLMProcessor):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt_template = ValidPromptTemplates.APPROACH_CODE_SUMMARY_PROCESSOR
        self.response_format_class = ApproachResponse

    def initialize(self):
        super().initialize()
        self.context["code_correctness"] = self.root_arguments.get("test_cases_score")

        self.context["code_efficiency"] = self.inputs["CodeEfficiencyProcessor"][
            "efficiency"
        ]
        self.context["code_efficiency"]["Score"] = round(
            self.context["code_efficiency"]["Score"] / 30 * 25
        )

        self.context["code_quality"] = self.inputs["CodeQualityProcessor"][
            "CodeQuality"
        ]
        self.context["code_quality"]["Score"] = round(
            self.context["code_quality"]["Score"] / 20 * 15
        )

        self.context["approach_score"] = self.inputs["ApproachDiscussionSaver"][
            "approach_score"
        ]

    def format_response(self, response: dict) -> dict:
        return {"Summary": response}
