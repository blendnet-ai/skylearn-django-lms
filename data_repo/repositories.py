import logging
import typing

from .models import InstituteData, ConfigMap

logger = logging.getLogger(__name__)
class InstituteDataRepository:

    @staticmethod
    def search_institutes_by_name(input_string):
        return InstituteData.objects.filter(institute_name__icontains=input_string)[:10]


class ConfigMapRepository:
    WHITELISTED_USER_EMAILS = "whitelisted_user_emails"
    ON_BOARDING_CODES = "onboarding_codes"
    PROACTIVE_BOT_MESSAGES = "proactive_bot_message_config"

    @staticmethod
    def get_config_by_tag(*, tag: str) -> typing.Union[typing.Dict, typing.List]:
        return ConfigMap.objects.get(tag = tag, is_active=True).config
