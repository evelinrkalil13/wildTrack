from sqlalchemy import Boolean, Column, DateTime, Enum as SAEnum, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from shared.base_model import Base
from shared.enums import AnimalSex


class Animal(Base):
    __tablename__ = "animals"

    id = Column(UUID(as_uuid=True), primary_key=True, nullable=False)
    rfid_tag = Column(String(100), nullable=True)
    species = Column(String(255), nullable=False)
    sex = Column(
        SAEnum(AnimalSex, name="animal_sex", create_type=False),
        nullable=False,
        server_default="unknown",
    )
    estimated_age = Column(String(100), nullable=True)
    is_identified = Column(Boolean, nullable=False, server_default="false")
    notes = Column(Text, nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
