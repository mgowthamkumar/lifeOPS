from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: Optional[str] = None
    preferences: Dict[str, Any] = {}
    context: Dict[str, Any] = {}

class UserContextUpdate(BaseModel):
    full_name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
