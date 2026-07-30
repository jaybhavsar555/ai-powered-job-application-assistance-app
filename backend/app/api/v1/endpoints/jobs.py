from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.schemas.job import JobCreate, JobResponse
from app.application.services.job import JobService

router = APIRouter()

@router.post("/ingest", response_model=JobResponse)
async def ingest_job(
    data: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingest a job via URL or raw text. Triggers the Job Intake Agent to normalize the description.
    """
    service = JobService(db)
    return await service.ingest_job(current_user.id, data)

@router.get("/", response_model=List[JobResponse])
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all jobs tracked by the user.
    """
    service = JobService(db)
    return await service.list_by_user(current_user.id)

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific job.
    """
    service = JobService(db)
    return await service.get_by_id(current_user.id, job_id)
