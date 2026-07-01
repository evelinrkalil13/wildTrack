from sqlalchemy import Column, DateTime, Enum as SAEnum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID

from shared.base_model import Base
from shared.enums import DeviceStatus


class Device(Base):
    __tablename__ = "devices"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    serial_number = Column(String(100), nullable=False)
    mac_address = Column(String(17), nullable=True)
    name = Column(String(255), nullable=True)
    station_id = Column(
        UUID(as_uuid=True),
        ForeignKey("stations.id", ondelete="SET NULL"),
        nullable=True,
    )
    status = Column(
        SAEnum(DeviceStatus, name="device_status", create_type=False),
        nullable=False,
        server_default="unassigned",
    )
    firmware_version = Column(String(50), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
