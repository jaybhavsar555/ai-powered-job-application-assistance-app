"""Obsidian second-brain API — sync applications + daily learning into a local vault."""

from datetime import date
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.application.services.obsidian_vault import DEFAULT_LEARNING_TRACKS, ObsidianVaultService
from app.domain.models import User

router = APIRouter()


class DailyLearningRequest(BaseModel):
    date: Optional[str] = Field(default=None, description="YYYY-MM-DD; default today")
    minutes: int = Field(default=45, ge=15, le=180)
    track_id: Optional[str] = None
    custom_focus: Optional[str] = None


@router.get("/status")
async def obsidian_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = ObsidianVaultService(db)
    return {
        **service.status(),
        "learning_tracks": DEFAULT_LEARNING_TRACKS,
    }


@router.post("/scaffold")
async def obsidian_scaffold(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = ObsidianVaultService(db)
    return await service.ensure_scaffold()


@router.post("/sync")
async def obsidian_sync_all(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Write/update Markdown notes for every application into the Obsidian vault."""
    service = ObsidianVaultService(db)
    return await service.sync_all(current_user.id)


@router.post("/sync/{application_id}")
async def obsidian_sync_one(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    service = ObsidianVaultService(db)
    path = await service.sync_application(current_user.id, application_id)
    return {"status": "ok", "file": path, **service.status()}


@router.post("/daily-learning")
async def obsidian_daily_learning(
    body: DailyLearningRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate today's fundamentals + code-practice note in Obsidian."""
    service = ObsidianVaultService(db)
    day = date.fromisoformat(body.date) if body.date else None
    return await service.write_daily_learning(
        current_user.id,
        day=day,
        minutes=body.minutes,
        track_id=body.track_id,
        custom_focus=body.custom_focus,
    )
