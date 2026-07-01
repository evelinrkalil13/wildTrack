from shared.base_exception import ConflictError, ForbiddenError, NotFoundError, WildTrackException


class StationFoodNotFoundError(NotFoundError):
    message = "Station food association not found"
    code = "NOT_FOUND"


class FoodAlreadyAssociatedError(ConflictError):
    message = "This food is already associated with the station"
    code = "FOOD_ALREADY_ASSOCIATED"


class CannotRemoveActiveFoodError(WildTrackException):
    message = "Cannot remove an active food association; deactivate it first"
    code = "CANNOT_REMOVE_ACTIVE"


class StationFoodAccessDeniedError(ForbiddenError):
    message = "You do not have permission to manage foods for this station"
    code = "FORBIDDEN"
