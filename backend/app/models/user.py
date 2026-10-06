from sqlalchemy import Column, String, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base import TimestampMixin, generate_uuid

class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    preferences = Column(JSON, default=dict, nullable=False)
    context = Column(JSON, default=dict, nullable=False)  # User context: skills, constraints, etc.

    # Relationships
    collections = relationship("Collection", back_populates="user", cascade="all, delete-orphan")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="user", cascade="all, delete-orphan")
