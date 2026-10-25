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