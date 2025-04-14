from .msteams import MSTeamsConferencePlatformService
from .zoom import ZoomConferencePlatformService
from django.conf import settings


def get_meeting_service():
    """Factory function to get configured meeting service"""
    provider = settings.MEETING_PROVIDER.lower()

    if provider == "teams":
        return MSTeamsConferencePlatformService
    elif provider == "zoom":
        return ZoomConferencePlatformService
    else:
        raise ValueError(f"Invalid meeting provider: {provider}")
