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


def get_meeting_service_by_provider(provider: str = None):
    """
    Determines which meeting service to use based on the provider field

    Args:
        provider (str, optional): Meeting provider ('teams' or 'zoom').
                                If None, uses default from settings.

    Returns:
        BaseConferencePlatformService: Instance of Teams or Zoom service
    """
    if not provider:
        return settings.MEETING_SERVICE()

    if provider.lower() == "teams":
        from meetings.services.msteams import MSTeamsConferencePlatformService

        return MSTeamsConferencePlatformService()
    elif provider.lower() == "zoom":
        from meetings.services.zoom import ZoomConferencePlatformService

        return ZoomConferencePlatformService()
    else:
        return settings.MEETING_SERVICE()  # fallback to default
