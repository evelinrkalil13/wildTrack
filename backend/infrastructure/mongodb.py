from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from shared.config import get_settings

# Collection name constants — all MongoDB access uses these, never raw strings.
COLLECTION_IOT_EVENTS = "iot_events"
COLLECTION_TELEMETRY = "device_telemetry"
COLLECTION_ALERTS = "alerts"
COLLECTION_MEDIA = "media_metadata"
COLLECTION_DEAD_LETTER = "dead_letter_events"

_settings = get_settings()

motor_client: AsyncIOMotorClient = AsyncIOMotorClient(_settings.mongodb_uri)
database: AsyncIOMotorDatabase = motor_client[_settings.mongodb_db]


def get_collection(name: str):
    return database[name]
