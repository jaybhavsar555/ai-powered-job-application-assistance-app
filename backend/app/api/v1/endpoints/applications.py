from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationStageUpdate,
    ApplicationResponse,
)
from app.application.services.application import ApplicationService

router = APIRouter()

@router.get("/", response_model=List[ApplicationResponse])
async def list_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all applications for the current user (Kanban board data)."""
    service = ApplicationService(db)
    return await service.list_by_user(current_user.id)

@router.post("/", response_model=ApplicationResponse)
async def create_application(
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an application for a tracked job (defaults to Wishlist)."""
    service = ApplicationService(db)
    return await service.create(current_user.id, data)

@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single application with job summary."""
    service = ApplicationService(db)
    return await service.get_by_id(current_user.id, application_id)

@router.patch("/{application_id}/stage", response_model=ApplicationResponse)
async def update_application_stage(
    application_id: UUID,
    data: ApplicationStageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move an application to a new pipeline stage (Kanban drag-drop)."""
    service = ApplicationService(db)
    return await service.update_stage(current_user.id, application_id, data.stage)
