from datetime import timezone
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from shared.config import get_settings

# Collection name constants — all MongoDB access uses these, never raw strings.
COLLECTION_IOT_EVENTS = "iot_events"
COLLECTION_TELEMETRY = "device_telemetry"
COLLECTION_ALERTS = "alerts"
COLLECTION_MEDIA = "media_metadata"
COLLECTION_DEAD_LETTER = "dead_letter_events"

_settings = get_settings()

# tz_aware=True + tzinfo=timezone.utc ensures all datetimes read from MongoDB
# come back as timezone-aware UTC objects, so Pydantic serializes them with
# the "+00:00" suffix. Without this, naive datetimes are returned and JavaScript
# misinterprets them as local time.
motor_client: AsyncIOMotorClient = AsyncIOMotorClient(
    _settings.mongodb_uri,
    tz_aware=True,
    tzinfo=timezone.utc,
)
database: AsyncIOMotorDatabase = motor_client[_settings.mongodb_db]


def get_collection(name: str):
    return database[name]
