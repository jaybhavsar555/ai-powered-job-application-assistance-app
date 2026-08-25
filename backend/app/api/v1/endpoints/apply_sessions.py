from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.application.services.apply_session import ApplySessionService

router = APIRouter()


class StartApplySessionRequest(BaseModel):
    application_id: Optional[UUID] = None
    job_id: Optional[UUID] = None
    reset: bool = False


class PatchFieldsRequest(BaseModel):
    fields: dict[str, str] = Field(default_factory=dict)


class ApproveStepRequest(BaseModel):
    step_id: Optional[str] = None


@router.patch("/{application_id}/fields")
async def patch_apply_fields(
    application_id: UUID,
    data: PatchFieldsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplySessionService(db)
    return await service.update_fields(current_user.id, application_id, data.fields)


@router.post("/start")
async def start_apply_session(
    data: StartApplySessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start Optim Hire–style Review & Apply session (HITL at each gate)."""
    service = ApplySessionService(db)
    return await service.start(
        current_user.id,
        application_id=data.application_id,
        job_id=data.job_id,
        reset=data.reset,
    )


@router.get("/{application_id}")
async def get_apply_session(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplySessionService(db)
    return await service.get(current_user.id, application_id)


@router.post("/{application_id}/approve")
async def approve_apply_step(
    application_id: UUID,
    data: ApproveStepRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = ApplySessionService(db)
    return await service.approve_step(
        current_user.id, application_id, step_id=data.step_id
    )


@router.post("/{application_id}/simulate-fill")
async def simulate_form_fill(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Advance showcase form-fill animation (does not submit to employer)."""
    service = ApplySessionService(db)
    return await service.simulate_fill(current_user.id, application_id)


@router.post("/{application_id}/confirm-submitted")
async def confirm_application_submitted(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """User confirms they clicked Submit on the employer site → Applied + follow-up."""
    service = ApplySessionService(db)
    return await service.confirm_submitted(current_user.id, application_id)
