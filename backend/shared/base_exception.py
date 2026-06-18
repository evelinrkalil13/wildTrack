class WildTrackException(Exception):
    message: str = "An error occurred"
    code: str = "INTERNAL_ERROR"

    def __init__(self, message: str | None = None) -> None:
        self.message = message if message is not None else self.__class__.message
        super().__init__(self.message)


class NotFoundError(WildTrackException):
    message = "Resource not found"
    code = "NOT_FOUND"


class ConflictError(WildTrackException):
    message = "Resource already exists"
    code = "CONFLICT"


class ForbiddenError(WildTrackException):
    message = "Access forbidden"
    code = "FORBIDDEN"


class UnauthorizedError(WildTrackException):
    message = "Unauthorized"
    code = "UNAUTHORIZED"
