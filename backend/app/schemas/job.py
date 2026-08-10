from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime

class JobCreate(BaseModel):
    # Plain str so relative / scrapy junk can be normalized in JobService
    url: Optional[str] = Field(default=None, max_length=2000)
    role_title: Optional[str] = None
    description_raw: Optional[str] = None
    company_name: Optional[str] = None

class NormalizedJob(BaseModel):
    role_title: str
    company_name: str
    required_skills: List[str]
    nice_to_have_skills: List[str]
    years_of_experience: Optional[int] = None
    responsibilities: List[str]
    benefits: List[str]

class JobResponse(BaseModel):
    id: UUID
    user_id: UUID
    company_id: Optional[UUID]
    url: Optional[str]
    role_title: str
    description_raw: str
    description_normalized: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
