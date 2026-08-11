from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Literal
from uuid import UUID
from datetime import datetime

ArtifactType = Literal["cover_letter", "resume"]
DecisionType = Literal["approve", "reject"]

class ApprovalDecisionRequest(BaseModel):
    artifact: ArtifactType
    decision: DecisionType
    job_id: Optional[UUID] = None
    application_id: Optional[UUID] = None
    # Payload from workflow final_state
    cover_letter: Optional[str] = None
    tailored_resume: Optional[Dict[str, Any]] = None
    ats_score: Optional[int] = None
    evidence: Optional[str] = None

class ApprovalDecisionResponse(BaseModel):
    application_id: UUID
    job_id: UUID
    artifact: ArtifactType
    decision: DecisionType
    stage: str
    cover_letter_id: Optional[UUID] = None
    resume_version_id: Optional[UUID] = None
    message: str
    decided_at: datetime

class ApprovalReevaluateRequest(BaseModel):
    job_id: UUID
    tailored_resume: Dict[str, Any]

class ApprovalReevaluateResponse(BaseModel):
    ats_score: int
    evidence: str
