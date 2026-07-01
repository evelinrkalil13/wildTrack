from pymongo.errors import DuplicateKeyError

from infrastructure.mongodb import (
    COLLECTION_DEAD_LETTER,
    COLLECTION_IOT_EVENTS,
    COLLECTION_TELEMETRY,
    get_collection,
)


class IotEventRepository:
    @staticmethod
    async def insert_event(document: dict) -> bool:
        """Returns True if inserted, False if duplicate event_id."""
        try:
            await get_collection(COLLECTION_IOT_EVENTS).insert_one(document)
            return True
        except DuplicateKeyError:
            return False

    @staticmethod
    async def insert_telemetry(document: dict) -> None:
        await get_collection(COLLECTION_TELEMETRY).insert_one(document)

    @staticmethod
    async def insert_dead_letter(document: dict) -> None:
        await get_collection(COLLECTION_DEAD_LETTER).insert_one(document)
