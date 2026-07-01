from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from modules.animals.exceptions import AnimalNotFoundError, RfidTagConflictError
from modules.animals.models import Animal
from modules.animals.repository import AnimalRepository
from modules.animals.schemas import (
    AnimalCreate,
    AnimalListResponse,
    AnimalRead,
    AnimalStationsRead,
    AnimalUpdate,
)
from shared.enums import AnimalSex, UserRole
from shared.pagination import make_paginated_response, paginate
from shared.uuid7 import generate_uuid7


def _is_admin(user) -> bool:
    role_val = user.role.value if hasattr(user.role, "value") else user.role
    return role_val == UserRole.admin.value


def _to_read(animal: Animal) -> AnimalRead:
    return AnimalRead(
        id=animal.id,
        rfid_tag=animal.rfid_tag,
        species=animal.species,
        sex=animal.sex,
        estimated_age=animal.estimated_age,
        is_identified=animal.is_identified,
        notes=animal.notes,
        created_at=animal.created_at,
        updated_at=animal.updated_at,
    )


class AnimalService:
    @staticmethod
    async def create_animal(
        session: AsyncSession, data: AnimalCreate, current_user
    ) -> AnimalRead:
        if data.rfid_tag is not None:
            existing = await AnimalRepository.find_by_rfid(session, data.rfid_tag)
            if existing is not None:
                raise RfidTagConflictError()

        animal = Animal(
            id=generate_uuid7(),
            rfid_tag=data.rfid_tag,
            species=data.species,
            sex=data.sex,
            estimated_age=data.estimated_age,
            is_identified=data.rfid_tag is not None,
            notes=data.notes,
        )
        animal = await AnimalRepository.create(session, animal)
        return _to_read(animal)

    @staticmethod
    async def get_animal(
        session: AsyncSession, animal_id: UUID, current_user
    ) -> AnimalRead:
        animal = await AnimalRepository.find_by_id(session, animal_id)
        if animal is None:
            raise AnimalNotFoundError()
        return _to_read(animal)

    @staticmethod
    async def list_animals(
        session: AsyncSession,
        page: int,
        page_size: int,
        current_user,
        species: Optional[str] = None,
        sex: Optional[AnimalSex] = None,
        is_identified: Optional[bool] = None,
    ) -> AnimalListResponse:
        offset, limit = paginate(page, page_size)
        animals, total = await AnimalRepository.list_all(
            session, offset, limit, species=species, sex=sex, is_identified=is_identified
        )
        items = [_to_read(a) for a in animals]
        return AnimalListResponse(**make_paginated_response(items, total, page, limit))

    @staticmethod
    async def update_animal(
        session: AsyncSession, animal_id: UUID, data: AnimalUpdate, current_user
    ) -> AnimalRead:
        animal = await AnimalRepository.find_by_id(session, animal_id)
        if animal is None:
            raise AnimalNotFoundError()

        update_data = data.model_dump(exclude_unset=True)

        if "rfid_tag" in update_data:
            new_tag = update_data["rfid_tag"]
            if new_tag is not None and new_tag != animal.rfid_tag:
                existing = await AnimalRepository.find_by_rfid(session, new_tag)
                if existing is not None:
                    raise RfidTagConflictError()
            update_data["is_identified"] = new_tag is not None

        for field, value in update_data.items():
            setattr(animal, field, value)

        animal = await AnimalRepository.update(session, animal)
        return _to_read(animal)

    @staticmethod
    async def delete_animal(
        session: AsyncSession, animal_id: UUID, current_user
    ) -> None:
        animal = await AnimalRepository.find_by_id(session, animal_id)
        if animal is None:
            raise AnimalNotFoundError()
        await AnimalRepository.soft_delete(session, animal)

    @staticmethod
    async def get_animal_stations(
        session: AsyncSession, animal_id: UUID, current_user
    ) -> AnimalStationsRead:
        animal = await AnimalRepository.find_by_id(session, animal_id)
        if animal is None:
            raise AnimalNotFoundError()
        # MongoDB query deferred to Slice 6 (iot_events ingestion not yet available)
        return AnimalStationsRead(
            animal_id=animal.id,
            rfid_tag=animal.rfid_tag,
            stations=[],
        )
