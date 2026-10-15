from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Text, ForeignKey, Boolean, DateTime, JSON, Table
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base import TimestampMixin, generate_uuid

decision_goals = Table(
    "decision_goals",
    Base.metadata,
    Column("decision_id", String(36), ForeignKey("decisions.id", ondelete="CASCADE"), primary_key=True),
    Column("goal_id", String(36), ForeignKey("goals.id", ondelete="CASCADE"), primary_key=True),
)

class Decision(Base, TimestampMixin):
    __tablename__ = "decisions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    question = Column(Text, nullable=False)
    context_description = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    constraints = Column(JSON, default=list, nullable=False)  # List of constraint strings or objects
    status = Column(String(50), default="DRAFT", nullable=False, index=True)  # DRAFT, ANALYZED, DECIDED, ARCHIVED
    selected_option_id = Column(String(36), nullable=True)

    # Relationships
    user = relationship("User", back_populates="decisions")
    goals = relationship("Goal", secondary=decision_goals, backref="decisions")
    options = relationship("DecisionOption", back_populates="decision", cascade="all, delete-orphan", order_by="DecisionOption.created_at")
    scenarios = relationship("Scenario", back_populates="decision", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="decision", cascade="all, delete-orphan", order_by="AnalysisResult.created_at.desc()")

    @property
    def latest_analysis(self):
        if self.analysis_results:
            ar = self.analysis_results[0]
            details = ar.details_json or {}
            options_data = details.get("options_analysis", [])
            return {
                "decision_id": ar.decision_id,
                "recommendation": ar.recommendation,
                "confidence": ar.confidence,
                "reasoning_summary": ar.reasoning_summary,
                "top_option_id": details.get("top_option_id"),
                "options_analysis": options_data,
                "created_at": ar.created_at,
            }
        return None

class DecisionOption(Base, TimestampMixin):
    __tablename__ = "decision_options"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    decision_id = Column(String(36), ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    match_score = Column(Float, nullable=True)  # 0.0 to 100.0
    effort_estimate = Column(String(100), nullable=True)

    # Relationships
    decision = relationship("Decision", back_populates="options")

class Scenario(Base, TimestampMixin):
    __tablename__ = "scenarios"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    decision_id = Column(String(36), ForeignKey("decisions.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    is_baseline = Column(Boolean, default=False, nullable=False)
    description = Column(Text, nullable=True)
    parameters = Column(JSON, default=dict, nullable=False)
    simulation_result = Column(JSON, default=dict, nullable=True)

    # Relationships
    user = relationship("User", back_populates="scenarios")
    decision = relationship("Decision", back_populates="scenarios")
    variables = relationship("ScenarioVariable", back_populates="scenario", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="scenario", cascade="all, delete-orphan")

class ScenarioVariable(Base):
    __tablename__ = "scenario_variables"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scenario_id = Column(String(36), ForeignKey("scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    variable_type = Column(String(50), default="string", nullable=False)  # number, string, boolean
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    scenario = relationship("Scenario", back_populates="variables")
