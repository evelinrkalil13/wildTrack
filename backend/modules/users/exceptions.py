from shared.base_exception import ForbiddenError, NotFoundError, WildTrackException


class UserNotFoundError(NotFoundError):
    message = "User not found"
    code = "USER_NOT_FOUND"


class InvalidCurrentPasswordError(WildTrackException):
    message = "Current password is incorrect"
    code = "INVALID_CURRENT_PASSWORD"


class CannotChangeOwnRoleError(ForbiddenError):
    message = "You cannot change your own role"
    code = "CANNOT_CHANGE_OWN_ROLE"
