from OpenAIService.repositories import PromptTemplateRepository


class PromptTemplateUsecase:
    @staticmethod
    def get_streaming_enabled_by_name(name):
        prompt_template = PromptTemplateRepository.get_by_name(name)

        if prompt_template is None or not prompt_template.streaming_enabled:
            return False
        return True

    @staticmethod
    def get_exists_by_name(name):
        prompt_template = PromptTemplateRepository.get_by_name(name)

        if prompt_template is not None:
            return True
        return False
