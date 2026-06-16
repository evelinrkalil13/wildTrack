from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.config import get_settings

_settings = get_settings()

_DATABASE_URL = (
    f"postgresql+asyncpg://{_settings.postgres_user}:{_settings.postgres_password}"
    f"@{_settings.postgres_host}:{_settings.postgres_port}/{_settings.postgres_db}"
)

engine = create_async_engine(
    _DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    echo=_settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session():
    async with AsyncSessionLocal() as session:
        yield session
