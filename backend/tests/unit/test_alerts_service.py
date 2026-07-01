import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from modules.alerts.exceptions import AlertNotFoundError
from modules.alerts.schemas import AlertListResponse, AlertRead
from modules.alerts.service import AlertService
from shared.enums import AlertType


def _make_alert_doc(**overrides) -> dict:
    base = {
        "alert_id": str(uuid.uuid4()),
        "alert_type": AlertType.connectivity_lost.value,
        "station_id": str(uuid.uuid4()),
        "device_id": str(uuid.uuid4()),
        "event_id": None,
        "message": "Device went offline",
        "resolved": False,
        "resolved_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return base


class TestRaiseAlert:
    async def test_inserts_when_no_open_alert(self):
        mock_insert = AsyncMock(return_value="some-id")
        with (
            patch(
                "modules.alerts.service.AlertRepository.find_open_alert",
                new=AsyncMock(return_value=None),
            ),
            patch(
                "modules.alerts.service.AlertRepository.insert_alert",
                new=mock_insert,
            ),
        ):
            await AlertService.raise_alert(
                alert_type=AlertType.connectivity_lost,
                station_id="station-1",
                device_id="device-1",
                message="offline",
            )
        mock_insert.assert_awaited_once()
        doc = mock_insert.call_args[0][0]
        assert doc["alert_type"] == AlertType.connectivity_lost.value
        assert doc["station_id"] == "station-1"
        assert doc["resolved"] is False

    async def test_deduplicates_existing_open_alert(self):
        existing = _make_alert_doc()
        mock_insert = AsyncMock()
        with (
            patch(
                "modules.alerts.service.AlertRepository.find_open_alert",
                new=AsyncMock(return_value=existing),
            ),
            patch(
                "modules.alerts.service.AlertRepository.insert_alert",
                new=mock_insert,
            ),
        ):
            await AlertService.raise_alert(
                alert_type=AlertType.connectivity_lost,
                station_id="station-1",
                message="offline again",
            )
        mock_insert.assert_not_awaited()


class TestResolveAlert:
    async def test_resolves_open_alert(self):
        alert_id = str(uuid.uuid4())
        open_doc = _make_alert_doc(alert_id=alert_id, resolved=False)
        resolved_doc = _make_alert_doc(
            alert_id=alert_id,
            resolved=True,
            resolved_at=datetime.now(timezone.utc),
        )
        mock_resolve = AsyncMock(return_value=True)
        with (
            patch(
                "modules.alerts.service.AlertRepository.find_by_alert_id",
                new=AsyncMock(side_effect=[open_doc, resolved_doc]),
            ),
            patch(
                "modules.alerts.service.AlertRepository.resolve_by_alert_id",
                new=mock_resolve,
            ),
        ):
            result = await AlertService.resolve_alert(alert_id)
        mock_resolve.assert_awaited_once()
        assert result.resolved is True

    async def test_raises_not_found_for_unknown_alert(self):
        with patch(
            "modules.alerts.service.AlertRepository.find_by_alert_id",
            new=AsyncMock(return_value=None),
        ):
            with pytest.raises(AlertNotFoundError):
                await AlertService.resolve_alert("nonexistent-id")


class TestListAlerts:
    async def test_returns_paginated_response(self):
        docs = [_make_alert_doc() for _ in range(3)]
        with patch(
            "modules.alerts.service.AlertRepository.list_alerts",
            new=AsyncMock(return_value=(docs, 3)),
        ):
            result = await AlertService.list_alerts(page=1, page_size=20)
        assert isinstance(result, AlertListResponse)
        assert result.total == 3
        assert len(result.items) == 3
        assert result.pages == 1
