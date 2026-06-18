from shared.base_exception import ConflictError, ForbiddenError
from shared.base_exception import UnauthorizedError as BaseUnauthorizedError


class EmailAlreadyExistsError(ConflictError):
    message = "Email is already registered"
    code = "EMAIL_ALREADY_EXISTS"


class InvalidCredentialsError(BaseUnauthorizedError):
    message = "Invalid email or password"
    code = "INVALID_CREDENTIALS"


class AccountInactiveError(ForbiddenError):
    message = "Account is inactive"
    code = "ACCOUNT_INACTIVE"
