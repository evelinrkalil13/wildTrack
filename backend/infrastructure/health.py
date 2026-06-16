import asyncio
import socket

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from infrastructure.minio_client import check_health as _minio_check
from infrastructure.mongodb import motor_client
from infrastructure.postgres import engine

router = APIRouter()


async def _probe_postgres() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        return True
    except Exception:
        return False


async def _probe_mongodb() -> bool:
    try:
        await motor_client.admin.command("ping")
        return True
    except Exception:
        return False


async def _probe_minio() -> bool:
    try:
        return await asyncio.get_event_loop().run_in_executor(None, _minio_check)
    except Exception:
        return False


async def _probe_mqtt() -> bool:
    from shared.config import get_settings

    s = get_settings()
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(s.mqtt_host, s.mqtt_port), timeout=3.0
        )
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


@router.get("/health", tags=["ops"])
async def health():
    postgres_ok, mongo_ok, minio_ok, mqtt_ok = await asyncio.gather(
        _probe_postgres(),
        _probe_mongodb(),
        _probe_minio(),
        _probe_mqtt(),
    )

    checks = {
        "postgres": "ok" if postgres_ok else "error",
        "mongodb": "ok" if mongo_ok else "error",
        "minio": "ok" if minio_ok else "error",
        "mqtt": "ok" if mqtt_ok else "error",
    }
    all_ok = all(v == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "ok" if all_ok else "degraded", "checks": checks},
    )
