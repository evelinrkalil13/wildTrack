from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from modules.alerts.schemas import AlertListResponse, AlertRead
from modules.alerts.service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    station_id: Optional[str] = Query(None),
    resolved: Optional[bool] = Query(None),
    current_user=Depends(get_current_user),
):
    return await AlertService.list_alerts(page, page_size, station_id, resolved)


@router.get("/{alert_id}", response_model=AlertRead)
async def get_alert(
    alert_id: str,
    current_user=Depends(get_current_user),
):
    return await AlertService.get_alert(alert_id)


@router.patch("/{alert_id}/resolve", response_model=AlertRead)
async def resolve_alert(
    alert_id: str,
    current_user=Depends(get_current_user),
):
    return await AlertService.resolve_alert(alert_id)
