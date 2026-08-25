from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any, Optional
from uuid import UUID
from pydantic import BaseModel, Field
from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.schemas.resume import ResumeCreate, ResumeUpdate, ResumeResponse
from app.application.services.resume import ResumeService
from app.application.services.resume_studio import ResumeStudioService

router = APIRouter()


class SaveTailorRequest(BaseModel):
    job_description: str = Field(..., min_length=1)
    tailored_resume: dict[str, Any]
    base_resume: str
    job_url: Optional[str] = None
    company_name: Optional[str] = None
    role_title: Optional[str] = None
    before_ats_score: Optional[int] = None
    after_ats_score: Optional[int] = None
    unified_ats: Optional[dict[str, Any]] = None
    job_id: Optional[UUID] = None
    application_id: Optional[UUID] = None
    approve_version: bool = False


class UpdateStudioContentRequest(BaseModel):
    tailored_resume: dict[str, Any]
    rescore: bool = True


@router.get("/studio")
async def list_resume_studio(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Tailored resume versions + workflow drafts for Resume Studio (no mock scores)."""
    service = ResumeStudioService(db)
    return await service.list_studio(current_user.id)


@router.get("/studio/{item_id}")
async def get_resume_studio_detail(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Side-by-side original vs tailored + ATS evidence + package download links."""
    service = ResumeStudioService(db)
    return await service.get_studio_detail(current_user.id, item_id)


@router.delete("/studio/{item_id}", status_code=204)
async def delete_resume_studio_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a resume version or clear a workflow draft."""
    service = ResumeStudioService(db)
    await service.delete_studio_item(current_user.id, item_id)


@router.post("/studio/save-tailor")
async def save_tailor_to_studio(
    data: SaveTailorRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Persist a standalone Tailor run into Resume Studio (draft or approved version)."""
    service = ResumeStudioService(db)
    return await service.save_tailor_run(
        current_user.id,
        job_description=data.job_description,
        tailored_resume=data.tailored_resume,
        base_resume=data.base_resume,
        job_url=data.job_url,
        company_name=data.company_name,
        role_title=data.role_title,
        before_score=data.before_ats_score,
        after_score=data.after_ats_score,
        unified_ats=data.unified_ats,
        job_id=data.job_id,
        application_id=data.application_id,
        approve_version=data.approve_version,
    )


@router.put("/studio/{item_id}/content")
async def update_studio_content(
    item_id: str,
    data: UpdateStudioContentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Structured edit of a studio draft/version with optional ATS re-score."""
    service = ResumeStudioService(db)
    return await service.update_studio_content(
        current_user.id,
        item_id,
        tailored_resume=data.tailored_resume,
        rescore=data.rescore,
    )


@router.post("/", response_model=ResumeResponse)
async def create_resume(
    data: ResumeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ResumeService(db)
    return await service.create(current_user.id, data)

@router.get("/", response_model=List[ResumeResponse])
async def list_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ResumeService(db)
    return await service.list_by_user(current_user.id)

@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ResumeService(db)
    return await service.get_by_id(current_user.id, resume_id)

@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: UUID,
    data: ResumeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ResumeService(db)
    return await service.update(current_user.id, resume_id, data)

@router.delete("/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ResumeService(db)
    await service.delete(current_user.id, resume_id)
