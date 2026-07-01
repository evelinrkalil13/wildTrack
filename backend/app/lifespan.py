import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from infrastructure.mongodb import motor_client
from infrastructure.postgres import engine
from modules.iot_events.processor import mqtt_subscriber_task

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(mqtt_subscriber_task())
    logger.info("MQTT subscriber task started")
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        motor_client.close()
        await engine.dispose()
        logger.info("MQTT subscriber task stopped")
