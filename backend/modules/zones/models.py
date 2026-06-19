from geoalchemy2 import Geometry
from sqlalchemy import Column, DateTime, Double, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID

from shared.base_model import Base


class Zone(Base):
    __tablename__ = "zones"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    name = Column(String(255), nullable=False)
    municipality = Column(String(255), nullable=True)
    city = Column(String(255), nullable=False)
    country = Column(String(100), nullable=False)
    altitude = Column(Double, nullable=True)
    latitude = Column(Numeric(10, 7, asdecimal=False), nullable=False)
    longitude = Column(Numeric(10, 7, asdecimal=False), nullable=False)
    geom = Column(Geometry("POINT", srid=4326, spatial_index=False), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
