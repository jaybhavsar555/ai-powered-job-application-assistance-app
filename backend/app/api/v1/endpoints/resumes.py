from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Any
from uuid import UUID
from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.schemas.resume import ResumeCreate, ResumeUpdate, ResumeResponse
from app.application.services.resume import ResumeService
from app.application.services.resume_studio import ResumeStudioService

router = APIRouter()


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
