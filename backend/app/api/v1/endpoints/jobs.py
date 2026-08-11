from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.schemas.job import JobCreate, JobResponse
from app.application.services.job import JobService
from app.application.services.quick_apply import QuickApplyService

router = APIRouter()


class QuickApplyFromPostRequest(BaseModel):
    post_text: str = Field(
        ...,
        min_length=40,
        description="Full LinkedIn hiring post or JD paste",
    )
    source_url: Optional[str] = Field(
        default=None,
        description="LinkedIn post URL (optional but recommended)",
    )
    contact_email: Optional[str] = Field(
        default=None,
        description="Override email if not found in the paste",
    )
    contact_name: Optional[str] = Field(
        default=None,
        description="Override contact name",
    )
    run_package: bool = Field(
        default=True,
        description="Tailor resume + write DOCX/PDF package",
    )
    candidate_name: Optional[str] = Field(
        default=None,
        description="Your name for the email sign-off",
    )


@router.post("/ingest", response_model=JobResponse)
async def ingest_job(
    data: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ingest a job via URL or raw text. Triggers the Job Intake Agent to normalize the description.
    """
    service = JobService(db)
    return await service.ingest_job(current_user.id, data)


@router.post("/quick-apply-from-post")
async def quick_apply_from_post(
    data: QuickApplyFromPostRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Paste a LinkedIn hiring post → wishlist job → tailor/package → email draft.

    mailto/Gmail cannot auto-attach files; download the tailored resume and attach it.
    """
    cand = data.candidate_name
    if not cand and current_user.email:
        cand = current_user.email.split("@")[0].replace(".", " ").title()
    service = QuickApplyService(db)
    return await service.from_hiring_post(
        current_user.id,
        post_text=data.post_text,
        source_url=data.source_url,
        contact_email_override=data.contact_email,
        contact_name_override=data.contact_name,
        run_package=data.run_package,
        candidate_name=cand,
    )


@router.get("", response_model=List[JobResponse])
@router.get("/", response_model=List[JobResponse], include_in_schema=False)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all jobs tracked by the user.
    Both /jobs and /jobs/ are registered so auth headers survive (no 307 redirect).
    """
    service = JobService(db)
    return await service.list_by_user(current_user.id)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific job."""
    service = JobService(db)
    return await service.get_by_id(current_user.id, job_id)
