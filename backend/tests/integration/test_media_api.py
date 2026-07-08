import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from modules.media.exceptions import DeviceNotFoundForMediaError, MediaUploadError


def _client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


_JPEG_STUB = b"\xff\xd8\xff\xe0" + b"\x00" * 20


class TestMediaUploadEndpoint:
    def test_returns_201_with_url(self):
        device_id = uuid.uuid4()
        event_id = str(uuid.uuid4())
        fake_url = f"http://localhost:9000/wildtrack-media/{device_id}/{event_id}.jpg"

        with patch(
            "modules.media.router.upload_device_photo",
            new=AsyncMock(
                return_value={"url": fake_url, "device_id": str(device_id), "event_id": event_id}
            ),
        ):
            r = _client().post(
                f"/api/v1/media/upload?device_id={device_id}&event_id={event_id}",
                content=_JPEG_STUB,
                headers={"Content-Type": "image/jpeg"},
            )

        assert r.status_code == 201
        body = r.json()
        assert body["url"] == fake_url
        assert body["device_id"] == str(device_id)
        assert body["event_id"] == event_id

    def test_returns_404_for_unknown_device(self):
        device_id = uuid.uuid4()
        event_id = str(uuid.uuid4())

        with patch(
            "modules.media.router.upload_device_photo",
            new=AsyncMock(side_effect=DeviceNotFoundForMediaError()),
        ):
            r = _client().post(
                f"/api/v1/media/upload?device_id={device_id}&event_id={event_id}",
                content=_JPEG_STUB,
                headers={"Content-Type": "image/jpeg"},
            )

        assert r.status_code == 404
        assert r.json()["error"] == "DEVICE_NOT_FOUND"

    def test_returns_400_on_storage_failure(self):
        device_id = uuid.uuid4()
        event_id = str(uuid.uuid4())

        with patch(
            "modules.media.router.upload_device_photo",
            new=AsyncMock(side_effect=MediaUploadError()),
        ):
            r = _client().post(
                f"/api/v1/media/upload?device_id={device_id}&event_id={event_id}",
                content=_JPEG_STUB,
                headers={"Content-Type": "image/jpeg"},
            )

        assert r.status_code == 400
        assert r.json()["error"] == "MEDIA_UPLOAD_ERROR"

    def test_returns_415_for_wrong_content_type(self):
        device_id = uuid.uuid4()
        event_id = str(uuid.uuid4())

        r = _client().post(
            f"/api/v1/media/upload?device_id={device_id}&event_id={event_id}",
            content=b"not a jpeg",
            headers={"Content-Type": "application/octet-stream"},
        )

        assert r.status_code == 415

    def test_returns_400_for_empty_body(self):
        device_id = uuid.uuid4()
        event_id = str(uuid.uuid4())

        r = _client().post(
            f"/api/v1/media/upload?device_id={device_id}&event_id={event_id}",
            content=b"",
            headers={"Content-Type": "image/jpeg"},
        )

        assert r.status_code == 400
        assert r.json()["error"] == "EMPTY_BODY"

    def test_returns_422_for_missing_query_params(self):
        r = _client().post(
            "/api/v1/media/upload",
            content=_JPEG_STUB,
            headers={"Content-Type": "image/jpeg"},
        )
        assert r.status_code == 422
