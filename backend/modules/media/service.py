import asyncio
import logging
from uuid import UUID

from infrastructure.minio_client import upload_jpeg
from infrastructure.postgres import AsyncSessionLocal
from modules.devices.repository import DeviceRepository
from modules.media.exceptions import DeviceNotFoundForMediaError, MediaUploadError
from shared.config import get_settings

logger = logging.getLogger(__name__)
_settings = get_settings()

_MAX_BYTES = 2 * 1024 * 1024  # 2 MB


async def upload_device_photo(
    device_id: UUID,
    event_id: str,
    data: bytes,
) -> dict:
    if len(data) > _MAX_BYTES:
        raise MediaUploadError(f"Image exceeds maximum size of {_MAX_BYTES // 1024} KB")

    async with AsyncSessionLocal() as session:
        device = await DeviceRepository.find_by_id(session, device_id)

    if device is None:
        raise DeviceNotFoundForMediaError()

    object_name = f"{device_id}/{event_id}.jpg"

    loop = asyncio.get_event_loop()
    try:
        url = await loop.run_in_executor(None, upload_jpeg, object_name, data)
    except Exception as exc:
        logger.error("MinIO upload failed for %s: %s", object_name, exc)
        raise MediaUploadError(f"Storage error: {exc}") from exc

    logger.info("Media uploaded: %s → %s", object_name, url)
    return {"url": url, "device_id": str(device_id), "event_id": event_id}
