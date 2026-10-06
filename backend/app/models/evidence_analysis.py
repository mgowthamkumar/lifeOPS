from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base import TimestampMixin, generate_uuid

class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    chunk_id = Column(String(36), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True, index=True)
    claim = Column(Text, nullable=False)
    extracted_text = Column(Text, nullable=False)
    source_filename = Column(String(255), nullable=False)
    page_number = Column(Integer, nullable=True)
    relevance_score = Column(Float, nullable=True)  # 0.0 to 1.0

    # Relationships
    document = relationship("Document")
    chunk = relationship("DocumentChunk")

class AnalysisResult(Base, TimestampMixin):
    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    decision_id = Column(String(36), ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False, index=True)
    scenario_id = Column(String(36), ForeignKey("scenarios.id", ondelete="SET NULL"), nullable=True, index=True)
    recommendation = Column(Text, nullable=False)
    confidence = Column(String(50), default="MEDIUM", nullable=False)  # HIGH, MEDIUM, LOW, INSUFFICIENT
    reasoning_summary = Column(Text, nullable=False)
    details_json = Column(JSON, default=dict, nullable=False)

    # Relationships
    decision = relationship("Decision", back_populates="analysis_results")
    scenario = relationship("Scenario", back_populates="analysis_results")

class ActivityLog(Base, TimestampMixin):
    __tablename__ = "activity_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    entity_type = Column(String(50), nullable=False)  # DOCUMENT, TASK, GOAL, DECISION, SCENARIO
    entity_id = Column(String(36), nullable=True)
    action = Column(String(50), nullable=False)  # CREATED, UPDATED, DELETED, ANALYZED, SIMULATED
    details = Column(Text, nullable=True)

    # Relationships
    user = relationship("User")
