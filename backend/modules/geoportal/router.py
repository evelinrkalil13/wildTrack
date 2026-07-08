from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user
from infrastructure.postgres import get_db_session
from modules.geoportal.schemas import GeoportalStationRead
from modules.geoportal.service import GeoportalService
from modules.users.models import User

router = APIRouter(prefix="/geoportal", tags=["geoportal"])


@router.get("/stations", response_model=list[GeoportalStationRead])
async def list_geoportal_stations(
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> list[GeoportalStationRead]:
    return await GeoportalService.list_stations(session)
