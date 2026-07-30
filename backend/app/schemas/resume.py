from pydantic import BaseModel
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime

class ResumeCreate(BaseModel):
    name: str
    content: Dict[str, Any]

class ResumeUpdate(BaseModel):
    name: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None

class ResumeResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    content: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
