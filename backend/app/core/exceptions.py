class BookingError(Exception):
    """Base class. The API layer catches this and returns an error response."""


class NotFoundError(BookingError):
    pass


class ValidationFailed(BookingError):
    pass


class ConflictError(BookingError):
    def __init__(self, message, conflicts=None):
        super().__init__(message)
        self.conflicts = conflicts or []

class AuthError(BookingError):
    """401: not logged in, bad credentials or bad token."""


class ForbiddenError(BookingError):
    """403: logged in, but the wrong role for this route."""