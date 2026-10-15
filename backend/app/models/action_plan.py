from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, Boolean, JSON, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base import TimestampMixin, generate_uuid

class ActionPlan(Base, TimestampMixin):
    __tablename__ = "action_plans"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    query = Column(Text, nullable=False, default="What should I do today?")
    summary = Column(Text, nullable=False)
    total_estimated_minutes = Column(Integer, default=0, nullable=False)
    available_minutes_constraint = Column(Integer, default=480, nullable=False)
    user_context_snapshot = Column(JSON, default=dict, nullable=False)
    status = Column(String(50), default="ACTIVE", nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="action_plans")
    items = relationship(
        "ActionPlanItem",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ActionPlanItem.priority",
    )

class ActionPlanItem(Base, TimestampMixin):
    __tablename__ = "action_plan_items"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    plan_id = Column(String(36), ForeignKey("action_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True, index=True)
    goal_id = Column(String(36), ForeignKey("goals.id", ondelete="SET NULL"), nullable=True, index=True)
    priority = Column(Integer, nullable=False)  # Rank: 1, 2, 3...
    priority_label = Column(String(50), nullable=False)  # e.g. "1 - URGENT", "2 - HIGH"
    action = Column(Text, nullable=False)
    reason = Column(Text, nullable=False)
    estimated_time = Column(String(100), nullable=False)  # e.g. "45 minutes"
    estimated_minutes = Column(Integer, default=0, nullable=False)
    evidence = Column(Text, nullable=False)
    confidence = Column(Float, default=0.9, nullable=False)  # 0.0 to 1.0
    confidence_level = Column(String(50), default="HIGH", nullable=False)  # HIGH, MEDIUM, LOW
    is_completed = Column(Boolean, default=False, nullable=False)

    # Relationships
    plan = relationship("ActionPlan", back_populates="items")
    task = relationship("Task")
    goal = relationship("Goal")
