from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.schemas.resume import ResumeCreate, ResumeUpdate, ResumeResponse
from app.application.services.resume import ResumeService

router = APIRouter()

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
