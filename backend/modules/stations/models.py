from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID

from shared.base_model import Base
from shared.enums import StationStatus


class Station(Base):
    __tablename__ = "stations"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    code = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id", ondelete="RESTRICT"), nullable=False)
    latitude = Column(Numeric(10, 7, asdecimal=False), nullable=False)
    longitude = Column(Numeric(10, 7, asdecimal=False), nullable=False)
    geom = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=False)
    status = Column(
        SAEnum(StationStatus, name="station_status", create_type=False),
        nullable=False,
        server_default="active",
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
