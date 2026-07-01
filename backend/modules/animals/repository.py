from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from modules.animals.models import Animal
from shared.enums import AnimalSex


class AnimalRepository:
    @staticmethod
    async def find_by_id(session: AsyncSession, animal_id: UUID) -> Optional[Animal]:
        result = await session.execute(
            select(Animal).where(Animal.id == animal_id, Animal.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def find_by_rfid(session: AsyncSession, rfid_tag: str) -> Optional[Animal]:
        result = await session.execute(
            select(Animal).where(
                Animal.rfid_tag == rfid_tag,
                Animal.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_all(
        session: AsyncSession,
        offset: int,
        limit: int,
        species: Optional[str] = None,
        sex: Optional[AnimalSex] = None,
        is_identified: Optional[bool] = None,
    ) -> tuple[list[Animal], int]:
        conditions = [Animal.deleted_at.is_(None)]
        if species is not None:
            conditions.append(Animal.species.ilike(f"%{species}%"))
        if sex is not None:
            conditions.append(Animal.sex == sex)
        if is_identified is not None:
            conditions.append(Animal.is_identified == is_identified)

        base = select(Animal).where(*conditions)
        count_result = await session.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar_one()

        result = await session.execute(
            base.order_by(Animal.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    @staticmethod
    async def create(session: AsyncSession, animal: Animal) -> Animal:
        session.add(animal)
        await session.commit()
        await session.refresh(animal)
        return animal

    @staticmethod
    async def update(session: AsyncSession, animal: Animal) -> Animal:
        await session.commit()
        await session.refresh(animal)
        return animal

    @staticmethod
    async def soft_delete(session: AsyncSession, animal: Animal) -> None:
        animal.deleted_at = datetime.now(timezone.utc)
        await session.commit()
