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
    auto_build_packets: Optional[bool] = None
    notify_email: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None


class ConfirmPacketBody(BaseModel):
    start_apply: bool = True
    generate_package: bool = False


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


@router.get("/packets")
async def list_packets(
    status: Optional[str] = None,
    run_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.application.services.job_packet import JobPacketService

    svc = JobPacketService(db)
    return {"packets": svc.list_packets(current_user.id, status=status, run_id=run_id)}


@router.get("/packets/{packet_id}")
async def get_packet(
    packet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.application.services.job_packet import JobPacketService

    svc = JobPacketService(db)
    return svc.get_packet(current_user.id, packet_id)


@router.post("/packets/{packet_id}/confirm")
async def confirm_packet(
    packet_id: str,
    body: ConfirmPacketBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User approved research + resume preview → ingest job and start Review & Apply."""
    from app.application.services.job_packet import JobPacketService

    svc = JobPacketService(db)
    return await svc.confirm_packet(
        current_user.id,
        packet_id,
        start_apply=body.start_apply,
        generate_package=body.generate_package,
    )


@router.post("/packets/{packet_id}/reject")
async def reject_packet(
    packet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.application.services.job_packet import JobPacketService

    svc = JobPacketService(db)
    return svc.reject_packet(current_user.id, packet_id)


@router.post("/packets/build-for-run/{run_id}")
async def build_packets_for_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually build research packets for an existing pipeline run."""
    from app.application.services.search_pipeline import SearchPipelineService
    from app.application.services.job_packet import JobPacketService
    from app.application.services.loop_notify import LoopNotifyService

    pipeline = SearchPipelineService(db)
    run = pipeline.get_run(current_user.id, run_id)
    pkt_svc = JobPacketService(db)
    built = await pkt_svc.build_packets_for_run(current_user.id, run)
    loop_svc = LoopEngineerService(db)
    notify = await LoopNotifyService(db).notify_packets_ready(
        current_user.id,
        run_id=run_id,
        schedule=loop_svc.get_schedule(current_user.id),
    )
    return {"packets": built, "notify": notify}
