from sqlalchemy import Boolean, Column, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID

from shared.base_model import Base


class StationFood(Base):
    __tablename__ = "station_foods"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    station_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stations.id", ondelete="CASCADE"),
        nullable=False,
    )
    food_id = Column(
        UUID(as_uuid=True),
        ForeignKey("foods.id", ondelete="RESTRICT"),
        nullable=False,
    )
    active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
