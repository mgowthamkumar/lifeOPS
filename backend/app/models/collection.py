from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base import TimestampMixin, generate_uuid

class Collection(Base, TimestampMixin):
    __tablename__ = "collections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="collections")
    documents = relationship("Document", back_populates="collection", cascade="all, delete-orphan")
