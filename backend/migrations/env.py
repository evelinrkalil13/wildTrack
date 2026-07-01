import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from shared.config import get_settings

config = context.config
fileConfig(config.config_file_name)

# Build the database URL from environment variables (overrides alembic.ini blank value).
def _db_url() -> str:
    settings = get_settings()
    return (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


config.set_main_option("sqlalchemy.url", _db_url())

from shared.base_model import Base
import modules.users.models  # noqa: F401 — registers User with Base.metadata
import modules.zones.models  # noqa: F401 — registers Zone with Base.metadata
import modules.stations.models  # noqa: F401 — registers Station with Base.metadata
import modules.user_stations.models  # noqa: F401 — registers UserStation with Base.metadata
import modules.devices.models  # noqa: F401 — registers Device with Base.metadata
import modules.animals.models  # noqa: F401 — registers Animal with Base.metadata
import modules.foods.models  # noqa: F401 — registers Food with Base.metadata
import modules.station_foods.models  # noqa: F401 — registers StationFood with Base.metadata

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
