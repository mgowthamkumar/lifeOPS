from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class RAGQueryRequest(BaseModel):
    collection_id: str = Field(..., description="Target knowledge base collection ID")
    question: str = Field(..., min_length=2, max_length=1000, description="User question to answer")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of context chunks to retrieve")
    relevance_threshold: float = Field(default=0.35, ge=0.0, le=1.0, description="Minimum cosine similarity required for relevance")

class RAGSource(BaseModel):
    document_id: str
    document_name: str
    chunk_index: int
    page_number: Optional[int] = None
    version: int = 1
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 - 1.0)")
    content_snippet: str

class RAGQueryResponse(BaseModel):
    question: str
    answer: str
    has_sufficient_evidence: bool
    confidence_score: float = Field(..., description="Confidence score (0.0 - 1.0)")
    sources: List[RAGSource] = Field(default_factory=list)
    collection_id: str
    retrieval_count: int
    model_used: str
    created_at: datetime
