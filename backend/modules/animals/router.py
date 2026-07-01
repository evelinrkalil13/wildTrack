from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_current_user, require_admin
from infrastructure.postgres import get_db_session
from modules.animals.schemas import (
    AnimalCreate,
    AnimalListResponse,
    AnimalRead,
    AnimalStationsRead,
    AnimalUpdate,
)
from modules.animals.service import AnimalService
from shared.enums import AnimalSex

router = APIRouter(prefix="/animals", tags=["animals"])


@router.post("", response_model=AnimalRead, status_code=201)
async def create_animal(
    data: AnimalCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await AnimalService.create_animal(session, data, current_user)


@router.get("", response_model=AnimalListResponse)
async def list_animals(
    species: Optional[str] = Query(None),
    sex: Optional[AnimalSex] = Query(None),
    is_identified: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await AnimalService.list_animals(
        session, page, page_size, current_user,
        species=species, sex=sex, is_identified=is_identified,
    )


@router.get("/{animal_id}", response_model=AnimalRead)
async def get_animal(
    animal_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await AnimalService.get_animal(session, animal_id, current_user)


@router.patch("/{animal_id}", response_model=AnimalRead)
async def update_animal(
    animal_id: UUID,
    data: AnimalUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await AnimalService.update_animal(session, animal_id, data, current_user)


@router.delete("/{animal_id}", status_code=204)
async def delete_animal(
    animal_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(require_admin),
):
    await AnimalService.delete_animal(session, animal_id, current_user)


@router.get("/{animal_id}/stations", response_model=AnimalStationsRead)
async def get_animal_stations(
    animal_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user=Depends(get_current_user),
):
    return await AnimalService.get_animal_stations(session, animal_id, current_user)
