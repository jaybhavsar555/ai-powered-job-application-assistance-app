from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

class WikiEntityCreate(BaseModel):
    entity_type: str
    title: str
    content: Dict[str, Any] = {}
    vector_id: Optional[UUID] = None

class WikiEntityUpdate(BaseModel):
    entity_type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[Dict[str, Any]] = None
    vector_id: Optional[UUID] = None

class WikiEntityResponse(BaseModel):
    id: UUID
    user_id: UUID
    entity_type: str
    title: str
    content: Dict[str, Any]
    vector_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
