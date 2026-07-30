from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

APPLICATION_STAGES = [
    "Wishlist",
    "Researching",
    "Ready",
    "Applied",
    "Interview",
    "Rejected",
]

class ApplicationCreate(BaseModel):
    job_id: UUID
    stage: str = "Wishlist"

class ApplicationStageUpdate(BaseModel):
    stage: str = Field(..., description="Wishlist | Researching | Ready | Applied | Interview | Rejected")

class JobSummary(BaseModel):
    id: UUID
    role_title: str
    url: Optional[str] = None
    status: str
    company_name: Optional[str] = None
    required_skills: List[str] = []

    class Config:
        from_attributes = True

class ApplicationResponse(BaseModel):
    id: UUID
    user_id: UUID
    job_id: UUID
    stage: str
    workflow_state: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime
    job: Optional[JobSummary] = None

    class Config:
        from_attributes = True
