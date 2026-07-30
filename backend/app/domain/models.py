from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, EmailStr, Field

class DomainBase(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserBase(DomainBase):
    email: EmailStr
    auth_provider: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    pass

class WikiEntity(DomainBase):
    user_id: UUID
    entity_type: str
    title: str
    content: Dict[str, Any] = Field(default_factory=dict)
    vector_id: Optional[UUID] = None

class Company(DomainBase):
    name: str
    research_data: Dict[str, Any] = Field(default_factory=dict)

class Job(DomainBase):
    user_id: UUID
    company_id: Optional[UUID] = None
    url: Optional[str] = None
    role_title: str
    description_raw: str
    description_normalized: Dict[str, Any] = Field(default_factory=dict)
    status: str = "Imported"

class ResumeBase(DomainBase):
    user_id: UUID
    name: str
    content: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True

class Application(DomainBase):
    user_id: UUID
    job_id: UUID
    stage: str = "Wishlist"  # Wishlist, Researching, Ready, Applied, Interview, Rejected
    workflow_state: Dict[str, Any] = Field(default_factory=dict)

class ResumeVersion(DomainBase):
    application_id: UUID
    base_resume_id: UUID
    tailored_content: Dict[str, Any] = Field(default_factory=dict)
    ats_score: Optional[int] = None
    feedback: List[Dict[str, Any]] = Field(default_factory=list)

class CoverLetter(DomainBase):
    application_id: UUID
    content_md: str
    letter_type: str = "Standard"

class Recruiter(DomainBase):
    company_id: UUID
    name: str
    linkedin_url: Optional[str] = None
    email: Optional[EmailStr] = None

class Message(DomainBase):
    application_id: UUID
    recruiter_id: Optional[UUID] = None
    content: str
    message_type: str = "Email"
    status: str = "Draft"
