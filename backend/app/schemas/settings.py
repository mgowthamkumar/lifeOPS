from typing import Optional
from pydantic import BaseModel, Field

class SettingsResponse(BaseModel):
    llm_provider: str
    llm_model: str
    llm_configured: bool
    embedding_backend: str
    embedding_model: str
    database_type: str
    database_path: str
    vector_store_type: str
    vector_store_path: str
    chunk_size: int
    chunk_overlap: int
    default_top_k: int
    default_relevance_threshold: float
    version: str
    environment: str

class SettingsUpdateRequest(BaseModel):
    default_top_k: Optional[int] = Field(None, ge=1, le=20)
    default_relevance_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)
    gemini_api_key: Optional[str] = None
