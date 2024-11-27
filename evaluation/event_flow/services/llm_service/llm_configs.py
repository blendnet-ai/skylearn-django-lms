import os
import yaml
from django.core.exceptions import ImproperlyConfigured


class LLMConfig:
    def __init__(self, name, type):
        self.name = name
        self.type = type

    @staticmethod
    def load_configs(directory='./llm_configs'):
        llm_instances = []
        for filename in os.listdir(directory):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                with open(os.path.join(directory, filename), 'r') as file:
                    config = yaml.safe_load(file)
                    name = config.get('name')
                    llm_type = config.get('type')
                    if not name or not type:
                        raise ImproperlyConfigured(f"Invalid configuration in {filename}")
                    llm_class = LLMConfig.get_llm_class(llm_type)
                    llm_instance = llm_class(**config)
                    llm_instances.append(llm_instance)
        return llm_instances

    @staticmethod
    def get_llm_class(llm_type):
        """Return the appropriate LLMConfig subclass based on type."""
        if llm_type == 'AzureOpenAILLMConfig':
            return AzureOpenAILLMConfig
        else:
            raise ImproperlyConfigured(f"Unsupported LLMConfig type: {llm_type}")


class AzureOpenAILLMConfig(LLMConfig):
    def __init__(self, name, type, endpoint, deployment_name, api_key, version):
        super().__init__(name, type)
        errors = []
        if not endpoint or not isinstance(endpoint, str):
            errors.append("Endpoint is required and must be a string")
        if not deployment_name or not isinstance(deployment_name, str):
            errors.append("Deployment name is required and must be a string")
        if not api_key or not isinstance(api_key, str):
            errors.append("API key is required and must be a string")
        if not version or not isinstance(version, str):
            errors.append("Version is required and must be a string")
        if errors:
            raise ImproperlyConfigured(", ".join(errors))
        self.name = name
        self.type = type
        self.endpoint = endpoint
        self.deployment_name = deployment_name
        self.api_key = api_key
        self.version = version

    def get_config(self):
        return {
            "name": self.name,
            "type": self.type,
            "endpoint": self.endpoint,
            "deployment_name": self.deployment_name,
            "api_key": self.api_key,
            "version": self.version
        }