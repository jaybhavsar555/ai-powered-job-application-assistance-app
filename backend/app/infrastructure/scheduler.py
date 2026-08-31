"""APScheduler tick for Loop Engineer scheduled scans."""

from __future__ import annotations

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _loop_engineer_tick() -> None:
    from app.application.services.loop_engineer import LoopEngineerService

    try:
        result = await LoopEngineerService.tick()
        logger.info("Loop Engineer scheduled tick finished: %s", result)
    except Exception:
        logger.exception("Loop Engineer scheduled tick failed")


def start_loop_engineer_scheduler() -> AsyncIOScheduler | None:
    global _scheduler
    settings = get_settings()
    if not getattr(settings, "LOOP_ENGINEER_ENABLED", True):
        logger.info("Loop Engineer scheduler disabled (LOOP_ENGINEER_ENABLED=false)")
        return None
    if _scheduler is not None:
        return _scheduler

    minutes = max(5, int(getattr(settings, "LOOP_ENGINEER_TICK_MINUTES", 30) or 30))
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _loop_engineer_tick,
        "interval",
        minutes=minutes,
        id="loop_engineer_tick",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Loop Engineer scheduler started (every %d min)", minutes)
    return _scheduler


def stop_loop_engineer_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Loop Engineer scheduler stopped")
