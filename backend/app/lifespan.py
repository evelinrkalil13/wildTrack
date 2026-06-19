from contextlib import asynccontextmanager

from fastapi import FastAPI

from infrastructure.mongodb import motor_client
from infrastructure.postgres import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    motor_client.close()
    await engine.dispose()
