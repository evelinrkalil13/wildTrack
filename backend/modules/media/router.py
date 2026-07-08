from uuid import UUID

from fastapi import APIRouter, Query, Request, status
from fastapi.responses import JSONResponse

from modules.media.exceptions import DeviceNotFoundForMediaError, MediaUploadError
from modules.media.service import upload_device_photo

router = APIRouter(prefix="/media", tags=["media"])

_MAX_BYTES = 2 * 1024 * 1024  # 2 MB


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_media(
    request: Request,
    device_id: UUID = Query(..., description="UUID of the device uploading the photo"),
    event_id: str = Query(..., description="event_id string from the feeding session"),
):
    """
    Accept a raw JPEG body from an ESP32 and store it in MinIO.

    No JWT required — device_id is validated against the devices table.
    Content-Type must be image/jpeg.
    Maximum body size: 2 MB.
    """
    content_type = request.headers.get("content-type", "")
    if "image/jpeg" not in content_type:
        return JSONResponse(
            status_code=415,
            content={"error": "UNSUPPORTED_MEDIA_TYPE", "message": "Content-Type must be image/jpeg"},
        )

    data = await request.body()
    if len(data) == 0:
        return JSONResponse(
            status_code=400,
            content={"error": "EMPTY_BODY", "message": "Request body is empty"},
        )

    result = await upload_device_photo(device_id, event_id, data)
    return result
