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
