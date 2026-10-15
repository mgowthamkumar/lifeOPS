from sqlalchemy import Column, String, Integer, Float, Text, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from app.database.base import Base
from app.models.base import TimestampMixin, generate_uuid

class EvidenceInvestigation(Base, TimestampMixin):
    __tablename__ = "evidence_investigations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(String(36), ForeignKey("collections.id", ondelete="SET NULL"), nullable=True, index=True)
    claim = Column(Text, nullable=False)
    status = Column(String(50), nullable=False)  # VERIFIED_SUPPORT, CONFLICT_DETECTED, CONTRADICTED, INSUFFICIENT_EVIDENCE
    has_sufficient_evidence = Column(Boolean, default=True, nullable=False)
    conflict_detected = Column(Boolean, default=False, nullable=False)
    confidence = Column(Float, default=0.0, nullable=False)
    uncertainty = Column(Float, default=0.0, nullable=False)
    uncertainty_level = Column(String(50), default="LOW", nullable=False)  # LOW, MEDIUM, HIGH
    reasoning_summary = Column(Text, nullable=False)
    conflicts_json = Column(JSON, default=list, nullable=False)
    evidence_items_json = Column(JSON, default=list, nullable=False)

    # Relationships
    user = relationship("User", back_populates="evidence_investigations")
    collection = relationship("Collection")
    evidence_items = relationship("Evidence", back_populates="investigation", cascade="all, delete-orphan")

class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    investigation_id = Column(String(36), ForeignKey("evidence_investigations.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True)
    chunk_id = Column(String(36), ForeignKey("document_chunks.id", ondelete="SET NULL"), nullable=True, index=True)
    chunk_index = Column(Integer, nullable=True)
    claim = Column(Text, nullable=False)
    extracted_text = Column(Text, nullable=False)
    source_filename = Column(String(255), nullable=False)
    page_number = Column(Integer, nullable=True)
    relevance_score = Column(Float, nullable=True)  # 0.0 to 1.0
    reasoning = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True)
    uncertainty = Column(Float, nullable=True)
    uncertainty_reasons = Column(JSON, default=list, nullable=True)
    stance = Column(String(50), default="SUPPORTS", nullable=True)  # SUPPORTS, CONTRADICTS, NEUTRAL

    # Relationships
    investigation = relationship("EvidenceInvestigation", back_populates="evidence_items")
    document = relationship("Document")
    chunk = relationship("DocumentChunk")
    user = relationship("User")

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
    entity_type = Column(String(50), nullable=False)  # DOCUMENT, TASK, GOAL, DECISION, SCENARIO, EVIDENCE
    entity_id = Column(String(36), nullable=True)
    action = Column(String(50), nullable=False)  # CREATED, UPDATED, DELETED, ANALYZED, SIMULATED, EXPLORED
    details = Column(Text, nullable=True)

    # Relationships
    user = relationship("User")
