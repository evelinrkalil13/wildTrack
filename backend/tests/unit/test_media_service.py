import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from modules.media.exceptions import DeviceNotFoundForMediaError, MediaUploadError
from modules.media.service import _MAX_BYTES, upload_device_photo


def _make_device():
    d = MagicMock()
    d.id = uuid.uuid4()
    return d


def _make_session_ctx(device=None):
    session = AsyncMock()
    session_return = device  # what find_by_id returns
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=None)
    factory = MagicMock(return_value=ctx)
    return factory, session


class TestUploadDevicePhoto:
    async def test_returns_url_for_registered_device(self):
        device = _make_device()
        device_id = device.id
        event_id = str(uuid.uuid4())
        fake_url = f"http://localhost:9000/wildtrack-media/{device_id}/{event_id}.jpg"

        factory, session = _make_session_ctx()
        with (
            patch("modules.media.service.AsyncSessionLocal", factory),
            patch(
                "modules.media.service.DeviceRepository.find_by_id",
                new=AsyncMock(return_value=device),
            ),
            patch(
                "modules.media.service.upload_jpeg",
                return_value=fake_url,
            ),
        ):
            result = await upload_device_photo(device_id, event_id, b"\xff\xd8\xff" + b"\x00" * 100)

        assert result["url"] == fake_url
        assert result["device_id"] == str(device_id)
        assert result["event_id"] == event_id

    async def test_raises_not_found_for_unknown_device(self):
        factory, session = _make_session_ctx()
        with (
            patch("modules.media.service.AsyncSessionLocal", factory),
            patch(
                "modules.media.service.DeviceRepository.find_by_id",
                new=AsyncMock(return_value=None),
            ),
        ):
            with pytest.raises(DeviceNotFoundForMediaError):
                await upload_device_photo(uuid.uuid4(), str(uuid.uuid4()), b"\xff\xd8\xff")

    async def test_raises_upload_error_when_minio_fails(self):
        device = _make_device()
        factory, session = _make_session_ctx()
        with (
            patch("modules.media.service.AsyncSessionLocal", factory),
            patch(
                "modules.media.service.DeviceRepository.find_by_id",
                new=AsyncMock(return_value=device),
            ),
            patch(
                "modules.media.service.upload_jpeg",
                side_effect=Exception("connection refused"),
            ),
        ):
            with pytest.raises(MediaUploadError):
                await upload_device_photo(device.id, str(uuid.uuid4()), b"\xff\xd8\xff")

    async def test_raises_upload_error_when_body_too_large(self):
        device = _make_device()
        factory, _ = _make_session_ctx()
        with (
            patch("modules.media.service.AsyncSessionLocal", factory),
            patch(
                "modules.media.service.DeviceRepository.find_by_id",
                new=AsyncMock(return_value=device),
            ),
        ):
            with pytest.raises(MediaUploadError):
                await upload_device_photo(device.id, str(uuid.uuid4()), b"\x00" * (_MAX_BYTES + 1))

    async def test_object_name_uses_device_and_event_ids(self):
        device = _make_device()
        device_id = device.id
        event_id = str(uuid.uuid4())
        captured_name: list[str] = []

        def _fake_upload(object_name, data):
            captured_name.append(object_name)
            return f"http://minio/{object_name}"

        factory, _ = _make_session_ctx()
        with (
            patch("modules.media.service.AsyncSessionLocal", factory),
            patch(
                "modules.media.service.DeviceRepository.find_by_id",
                new=AsyncMock(return_value=device),
            ),
            patch("modules.media.service.upload_jpeg", side_effect=_fake_upload),
        ):
            await upload_device_photo(device_id, event_id, b"\xff\xd8\xff")

        assert captured_name[0] == f"{device_id}/{event_id}.jpg"
