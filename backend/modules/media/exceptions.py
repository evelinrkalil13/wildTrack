from shared.base_exception import NotFoundError, WildTrackException


class DeviceNotFoundForMediaError(NotFoundError):
    message = "Device not found or is not registered"
    code = "DEVICE_NOT_FOUND"


class MediaUploadError(WildTrackException):
    message = "Failed to upload media file"
    code = "MEDIA_UPLOAD_ERROR"
