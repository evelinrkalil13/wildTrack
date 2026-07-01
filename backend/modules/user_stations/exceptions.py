from shared.base_exception import ConflictError, ForbiddenError, NotFoundError, WildTrackException


class MemberNotFoundError(NotFoundError):
    message = "Station member not found"
    code = "NOT_FOUND"


class AlreadyMemberError(ConflictError):
    message = "This user is already a member of the station"
    code = "ALREADY_MEMBER"


class CannotAssignOwnerError(WildTrackException):
    message = "Cannot assign the owner role via this endpoint"
    code = "CANNOT_ASSIGN_OWNER"


class CannotChangeOwnerRoleError(WildTrackException):
    message = "Cannot change the role of the station owner"
    code = "CANNOT_CHANGE_OWNER"


class CannotRemoveOwnerError(WildTrackException):
    message = "Cannot remove the station owner"
    code = "CANNOT_REMOVE_OWNER"


class MemberAccessDeniedError(ForbiddenError):
    message = "You do not have permission to manage members of this station"
    code = "FORBIDDEN"
