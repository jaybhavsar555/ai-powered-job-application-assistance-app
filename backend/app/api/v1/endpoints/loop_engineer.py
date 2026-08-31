"""Loop Engineer API — watchlist, schedule, and on-demand scans."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.application.services.loop_engineer import LoopEngineerService
from app.domain.models import User

router = APIRouter()


class WatchCompanyBody(BaseModel):
    name: str
    careers_url: str = ""
    ats_host: str = ""
    priority: str = "normal"
    notes: str = ""


class SchedulePatch(BaseModel):
    enabled: Optional[bool] = None
    interval_hours: Optional[int] = Field(default=None, ge=1, le=168)
    watchlist_only: Optional[bool] = None
    resume_refresh_hint: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None


@router.get("/status")
async def loop_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    return await svc.status(current_user.id)


@router.get("/watchlist")
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    return {"watchlist": await svc.list_watchlist(current_user.id)}


@router.post("/watchlist")
async def add_watchlist_company(
    body: WatchCompanyBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    company = await svc.add_watch_company(
        current_user.id,
        name=body.name,
        careers_url=body.careers_url,
        ats_host=body.ats_host,
        priority=body.priority,
        notes=body.notes,
    )
    await db.commit()
    return {"company": company}


@router.delete("/watchlist/{entity_id}")
async def remove_watchlist_company(
    entity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    return await svc.remove_watch_company(current_user.id, entity_id)


@router.post("/watchlist/seed-examples")
async def seed_watchlist_examples(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    result = await svc.seed_example_watchlist(current_user.id)
    await db.commit()
    return result


@router.get("/schedule")
async def get_schedule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    return {"schedule": svc.get_schedule(current_user.id)}


@router.put("/schedule")
async def update_schedule(
    body: SchedulePatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    patch = body.model_dump(exclude_unset=True)
    return {"schedule": svc.save_schedule(current_user.id, patch)}


@router.post("/run-now")
async def run_now(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an immediate Loop Engineer scan (Ollama/Kimi/DeepSeek via runtime LLM)."""
    svc = LoopEngineerService(db)
    return await svc.run_scan(current_user.id, trigger="manual")


@router.get("/digest")
async def loop_digest(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    return {"lines": svc.digest_lines(current_user.id)}
