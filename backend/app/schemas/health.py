from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel

class DatabaseHealth(BaseModel):
    connected: bool
    type: str
    message: str

class VectorDBHealth(BaseModel):
    configured: bool
    persist_dir: str
    status: str

class LLMHealth(BaseModel):
    provider: str
    configured: bool
    model: str
    message: str

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    app_name: str
    version: str
    database: DatabaseHealth
    vector_db: VectorDBHealth
    llm: LLMHealth
    environment: str
