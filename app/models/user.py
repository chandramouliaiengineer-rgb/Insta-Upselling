from sqlalchemy import Column, String, Integer, DateTime, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
import enum
from app.database import Base

class UserStatus(str, enum.Enum):
    cold = "cold"
    warm = "warm"
    hot = "hot"
    converted = "converted"

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instagram_user_id = Column(String, unique=True, nullable=False)
    messaging_psid = Column(String, unique=True, nullable=True)  # NEW - real messaging ID, captured from private reply response
    username = Column(String, nullable=False)
    email = Column(String, nullable=True)
    whatsapp = Column(String, nullable=True)
    lead_score = Column(Integer, default=0)
    status = Column(SAEnum(UserStatus), default=UserStatus.cold)
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_active_at = Column(DateTime(timezone=True), onupdate=func.now())
