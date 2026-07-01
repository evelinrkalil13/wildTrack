from shared.base_exception import ConflictError, NotFoundError, WildTrackException


class FoodNotFoundError(NotFoundError):
    message = "Food not found"
    code = "NOT_FOUND"


class FoodNameConflictError(ConflictError):
    message = "A food with this name already exists"
    code = "FOOD_NAME_EXISTS"


class FoodInUseError(WildTrackException):
    message = "Cannot delete a food that is the active configuration for a station"
    code = "FOOD_IN_USE"
