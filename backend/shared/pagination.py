import math
from typing import Generic, Sequence, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


def paginate(page: int, page_size: int) -> tuple[int, int]:
    """Return (offset, limit) clamped to valid ranges."""
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    return (page - 1) * page_size, page_size


def make_paginated_response(
    items: Sequence,
    total: int,
    page: int,
    page_size: int,
) -> dict:
    return {
        "items": list(items),
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if page_size > 0 else 0,
    }
