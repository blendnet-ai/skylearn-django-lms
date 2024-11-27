import logging
import random

from django.conf import settings
from openai import AzureOpenAI,OpenAI
from .llm_configs import LLMConfig, AzureOpenAILLMConfig

logger = logging.getLogger(__name__)

class OpenAIService:

    def __init__(self):
        self.api_key = settings.AZURE_OPENAI_API_KEY_OLD
        self.delimiter = "####"
        self.api_base = settings.AZURE_OPENAI_AZURE_ENDPOINT_OLD
        self.api_version = "2024-02-15-preview"
        self.response_so_far = {}
        llm_instances:[AzureOpenAILLMConfig] = LLMConfig.load_configs()
        self.llm_configs = {}
        for llm_instance in llm_instances:
            self.llm_configs[llm_instance.name] = {
                "api_key":llm_instance.api_key,
                "api_version": llm_instance.version,
                "azure_endpoint": llm_instance.endpoint,
                "azure_deployment": llm_instance.deployment_name,
            }

    def get_delimiter(self):
        return self.delimiter

    def get_completion_from_message_public(self, messages, max_tokens=3000, temperature=0, model="gpt-3.5-turbo"):
        client = OpenAI(
            api_key="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",
        )

        response = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None
        )

        return response.choices[0].message.content

    def get_completion_from_messages(self, messages, model="gpt4-32k", max_tokens=10000, temperature=0,
                                     llm_config_name=None, llm_config_name_options=None):
        if llm_config_name:
            if llm_config_name not in self.llm_configs:
                raise ValueError(f"Unexpected llm config name - {llm_config_name}. Valid values - {self.llm_configs.keys()}")
            client = AzureOpenAI(
                **self.llm_configs.get(llm_config_name)
            )
            logger.info(f"Using LLMConfig {llm_config_name}")
        elif llm_config_name_options:
            llm_config_name = random.choice(llm_config_name_options)
            if llm_config_name not in self.llm_configs:
                raise ValueError(f"Unexpected llm config name - {llm_config_name}. Valid values - {self.llm_configs.keys()}")
            client = AzureOpenAI(
                **self.llm_configs.get(llm_config_name)
            )
            logger.info(f"Using LLMConfig {llm_config_name}")
        else:
            client = AzureOpenAI(
                api_key=self.api_key,
                api_version=self.api_version,
                azure_endpoint=self.api_base,
                azure_deployment=model
            )

        response = client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=0.95,
            frequency_penalty=0,
            presence_penalty=0,
            stop=None
        )
        return response.choices[0].message.content