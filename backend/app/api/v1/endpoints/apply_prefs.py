from typing import Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.application.services.apply_prefs import ApplyPrefsService
from app.application.services.auto_apply_bot import AutoApplyBot

router = APIRouter()


class ApplyPrefsUpdate(BaseModel):
    apply_mode: Optional[str] = Field(
        None, description="review_and_apply | auto_apply"
    )
    auto_consent: Optional[bool] = None
    min_confidence: Optional[float] = Field(None, ge=0.5, le=1.0)
    work_authorization: Optional[str] = Field(
        None,
        description="citizen | opt | needs_sponsorship | other",
    )


class ExtensionEventIn(BaseModel):
    event_type: str = Field(
        ...,
        description="evaluate | filled | submit_attempt | submitted | skip | reapply",
    )
    host: str = ""
    url: Optional[str] = None
    application_id: Optional[str] = None
    confidence: float = 0.0
    reason: Optional[str] = None
    detail: Optional[str] = None


@router.get("")
@router.get("/", include_in_schema=False)
async def get_apply_prefs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ApplyPrefsService(db).get(current_user.id)


@router.put("")
@router.put("/", include_in_schema=False)
async def update_apply_prefs(
    data: ApplyPrefsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    patch = data.model_dump(exclude_none=True)
    return await ApplyPrefsService(db).save(current_user.id, patch)


@router.get("/skip-queue")
async def list_skip_queue(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prefs = await ApplyPrefsService(db).get(current_user.id)
    return {"items": prefs.get("skip_queue") or []}
