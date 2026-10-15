from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class EvidenceExploreRequest(BaseModel):
    claim: str = Field(..., min_length=1, description="The claim, assertion, or question to investigate across evidence documents")
    collection_id: Optional[str] = Field(None, description="Optional collection ID to scope retrieval to. If omitted, searches all accessible collections.")
    top_k: int = Field(6, ge=1, le=20, description="Maximum number of candidate chunks to evaluate")
    relevance_threshold: float = Field(0.30, ge=0.0, le=1.0, description="Minimum cosine relevance threshold")

class EvidenceItem(BaseModel):
    id: str
    claim: str
    document_id: Optional[str] = None
    source_filename: str
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None
    chunk_id: Optional[str] = None
    chunk_text: str
    relevance: float  # 0.0 to 1.0
    reasoning: str
    confidence: float  # 0.0 to 1.0
    uncertainty: float  # 0.0 to 1.0
    uncertainty_reasons: List[str] = Field(default_factory=list)
    stance: str  # SUPPORTS, CONTRADICTS, NEUTRAL

class ConflictSourceDetail(BaseModel):
    document_name: str
    document_id: Optional[str] = None
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None
    chunk_text: str
    assertion: str

class EvidenceConflictItem(BaseModel):
    topic: str
    source_a: ConflictSourceDetail
    source_b: ConflictSourceDetail
    discrepancy_explanation: str
    severity: str = "HIGH"  # HIGH, MEDIUM, LOW
    suggested_resolution: Optional[str] = None

class EvidenceExploreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    investigation_id: str
    claim: str
    status: str  # VERIFIED_SUPPORT, CONFLICT_DETECTED, CONTRADICTED, INSUFFICIENT_EVIDENCE
    has_sufficient_evidence: bool
    conflict_detected: bool
    confidence: float
    uncertainty: float
    uncertainty_level: str  # LOW, MEDIUM, HIGH
    reasoning_summary: str
    evidence_items: List[EvidenceItem] = Field(default_factory=list)
    conflicts: List[EvidenceConflictItem] = Field(default_factory=list)
    collection_id: Optional[str] = None
    total_sources_evaluated: int = 0
    created_at: datetime

class EvidenceInvestigationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim: str
    status: str
    conflict_detected: bool
    confidence: float
    uncertainty: float
    uncertainty_level: str
    sources_count: int
    created_at: datetime
