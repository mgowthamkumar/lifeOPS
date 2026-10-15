from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class CollectionBase(BaseModel):
    name: str
    description: Optional[str] = None

class CollectionCreate(CollectionBase):
    pass

class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class CollectionResponse(CollectionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    document_count: int = 0
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime
