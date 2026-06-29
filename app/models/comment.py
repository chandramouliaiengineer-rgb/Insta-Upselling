from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.database import Base

class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    instagram_comment_id = Column(String, unique=True, nullable=False)
    post_id = Column(UUID(as_uuid=True), ForeignKey("posts.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    text = Column(Text, nullable=False)
    username = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=True)
    replied = Column(Boolean, default=False)
    replied_at = Column(DateTime(timezone=True), nullable=True)
    our_reply_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
