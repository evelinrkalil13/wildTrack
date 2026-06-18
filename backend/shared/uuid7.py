import uuid as _uuid

from uuid_extensions import uuid7 as _uuid7


def generate_uuid7() -> _uuid.UUID:
    return _uuid7()
