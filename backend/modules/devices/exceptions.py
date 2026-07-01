from shared.base_exception import ConflictError, ForbiddenError, NotFoundError, WildTrackException


class DeviceNotFoundError(NotFoundError):
    message = "Device not found"
    code = "NOT_FOUND"


class SerialNumberConflictError(ConflictError):
    message = "A device with this serial number already exists"
    code = "SERIAL_EXISTS"


class DeviceAlreadyAssignedError(WildTrackException):
    message = "Device is already assigned to a station"
    code = "DEVICE_ALREADY_ASSIGNED"


class DeviceNotAssignedError(WildTrackException):
    message = "Device is not currently assigned to any station"
    code = "DEVICE_NOT_ASSIGNED"


class StationHasDeviceError(WildTrackException):
    message = "The target station already has an active device"
    code = "STATION_HAS_DEVICE"


class DeviceAccessDeniedError(ForbiddenError):
    message = "You do not have access to this device"
    code = "FORBIDDEN"
