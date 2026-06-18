from shared.base_exception import NotFoundError


class UserNotFoundError(NotFoundError):
    message = "User not found"
    code = "USER_NOT_FOUND"
