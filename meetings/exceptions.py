class ConferencePlatformError(Exception):
    """Base exception for conference platform errors"""

    pass


class TeamsAuthenticationError(ConferencePlatformError):
    """Raised when Teams authentication fails"""

    pass


class TeamsMeetingCreationError(ConferencePlatformError):
    """Raised when Teams meeting creation fails"""

    pass


class TeamsMeetingDeletionError(ConferencePlatformError):
    """Raised when Teams meeting deletion fails"""

    pass


class MeetingNotFoundError(Exception):
    """Exception raised when a meeting is not found."""
    pass

class PresenterDetailsMissingError(Exception):
    """Exception raised when presenter details are missing."""
    pass

class ConferenceIDMissingError(Exception):
    """Exception raised when presenter details are missing."""
    pass


class SeriesNotFoundError(Exception):
    """Exception raised when series are missing."""
    pass

class NoMeetingsFoundError(Exception):
    """Exception raised when series are missing."""
    pass