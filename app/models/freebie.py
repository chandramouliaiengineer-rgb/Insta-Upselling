from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base


class Freebie(Base):
    __tablename__ = "freebies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic = Column(String, nullable=False)
    title = Column(String, nullable=False)
    type = Column(String, default="guide")
    file_url = Column(String, nullable=False)
    threshold = Column(Integer, default=30)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class DeliveredFreebie(Base):
    __tablename__ = "delivered_freebies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    freebie_id = Column(UUID(as_uuid=True), ForeignKey("freebies.id"), nullable=False)
    username = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    delivered_at = Column(DateTime(timezone=True), server_default=func.now())
