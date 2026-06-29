from sqlalchemy import Column, String, Integer, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from app.database import Base


class InterestSignal(Base):
    __tablename__ = "interest_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    username = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    intent = Column(String, nullable=False)
    weight = Column(Integer, default=0)
    source = Column(String, default="comment")
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InterestProfile(Base):
    __tablename__ = "interest_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, nullable=False)
    username = Column(String, nullable=False)
    primary_topic = Column(String, nullable=True)
    topic_scores = Column(JSONB, default={})
    total_score = Column(Float, default=0)
    price_check_count = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
