from shared.base_exception import ConflictError, NotFoundError, WildTrackException


class ZoneNotFoundError(NotFoundError):
    message = "Zone not found"
    code = "ZONE_NOT_FOUND"


class ZoneNameConflictError(ConflictError):
    message = "A zone with this name already exists in this country"
    code = "ZONE_NAME_EXISTS"


class ZoneHasActiveStationsError(WildTrackException):
    message = "Cannot delete a zone that has active stations"
    code = "ZONE_HAS_STATIONS"
