from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base import TimestampMixin, generate_uuid

class Goal(Base, TimestampMixin):
    __tablename__ = "goals"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    importance = Column(String(50), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String(50), default="ACTIVE", nullable=False, index=True)  # ACTIVE, IN_PROGRESS, ACHIEVED, CANCELLED
    progress = Column(Float, default=0.0, nullable=False)  # 0.0 to 100.0

    # Relationships
    user = relationship("User", back_populates="goals")
    tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan")

class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    goal_id = Column(String(36), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    priority = Column(String(50), default="MEDIUM", nullable=False)  # LOW, MEDIUM, HIGH, URGENT
    estimated_duration_minutes = Column(Integer, default=60, nullable=False)
    status = Column(String(50), default="TODO", nullable=False, index=True)  # TODO, IN_PROGRESS, COMPLETED, BLOCKED, CANCELLED
    category = Column(String(100), nullable=True)

    # Relationships
    user = relationship("User", back_populates="tasks")
    goal = relationship("Goal", back_populates="tasks")
