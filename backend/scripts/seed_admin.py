import asyncio

from infrastructure.postgres import AsyncSessionLocal
from modules.users.repository import UserRepository
from shared.config import get_settings
from shared.enums import UserRole
from shared.security import hash_password
from shared.uuid7 import generate_uuid7


async def seed_admin() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        existing = await UserRepository.find_by_email(session, settings.admin_seed_email)
        if existing:
            print(f"Admin already exists: {settings.admin_seed_email}")
            return
        user = await UserRepository.create(
            session,
            {
                "id": generate_uuid7(),
                "name": "Admin",
                "document": "ADMIN-00",
                "email": settings.admin_seed_email,
                "password_hash": hash_password(settings.admin_seed_password),
                "role": UserRole.admin,
            },
        )
        print(f"Admin created: {user.email}")


if __name__ == "__main__":
    asyncio.run(seed_admin())
