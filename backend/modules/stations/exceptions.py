from shared.base_exception import ConflictError, ForbiddenError, NotFoundError


class StationNotFoundError(NotFoundError):
    message = "Station not found"
    code = "NOT_FOUND"


class StationCodeConflictError(ConflictError):
    message = "A station with this code already exists"
    code = "STATION_CODE_EXISTS"


class StationAccessDeniedError(ForbiddenError):
    message = "You do not have access to this station"
    code = "FORBIDDEN"
