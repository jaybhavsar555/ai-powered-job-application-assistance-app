"""
Loop Engineer v1 — company watchlist + scheduled Search Pipeline scans.

Uses local/open models (Ollama, Kimi via Token Harbor) through existing
JobDiscoveryAgent + SearchPipelineService. Never auto-approves or auto-applies;
scheduled runs stop at awaiting_shortlist and surface in Inbox digest.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import get_settings
from app.infrastructure.db.models import DBWikiEntity
from app.schemas.knowledge import WikiEntityCreate
from app.application.services.knowledge import KnowledgeBaseService

logger = logging.getLogger(__name__)

ENTITY_TYPE_WATCH = "company_watch"
ENTITY_TYPE_SCHEDULE = "loop_schedule"
SCHEDULE_TITLE = "loop_engineer_schedule"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


def _loop_root() -> Path:
    settings = get_settings()
    root = Path(getattr(settings, "LOOP_ENGINEER_DIR", None) or "./data/loop_engineer")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _user_schedule_path(user_id: UUID) -> Path:
    d = _loop_root() / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / "schedule.json"


class LoopEngineerService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.kb = KnowledgeBaseService(db)
        self.settings = get_settings()

    def default_schedule(self) -> Dict[str, Any]:
        return {
            "enabled": False,
            "interval_hours": max(
                1, int(getattr(self.settings, "LOOP_ENGINEER_INTERVAL_HOURS", 24) or 24)
            ),
            "watchlist_only": False,
            "last_run_at": None,
            "last_run_id": None,
            "last_run_jobs": 0,
            "last_error": None,
            "preferences": {
                "targetRoles": "software engineer",
                "minSalary": "0",
                "locationHubs": ["Remote"],
                "isRemote": True,
                "companyTypes": [],
                "techStack": "",
                "experienceLevel": "",
                "workAuthorization": "",
            },
            "resume_refresh_hint": True,
            "auto_build_packets": True,
            "notify_email": True,
            "philosophy": (
                "Loop Engineer scans on a schedule, scores with your local/cloud LLM, "
                "then waits for your shortlist approval in Pipeline — no silent apply."
            ),
        }

    async def list_watchlist(self, user_id: UUID) -> List[Dict[str, Any]]:
        entities = await self.kb.get_by_user_id(user_id)
        out: List[Dict[str, Any]] = []
        for e in entities:
            if getattr(e, "entity_type", None) != ENTITY_TYPE_WATCH:
                continue
            content = dict(e.content or {})
            out.append(
                {
                    "id": str(e.id),
                    "name": e.title or content.get("name") or "Company",
                    "careers_url": content.get("careers_url") or content.get("url") or "",
                    "ats_host": content.get("ats_host") or "",
                    "priority": content.get("priority") or "normal",
                    "notes": content.get("notes") or "",
                    "portfolio_sync": bool(content.get("portfolio_sync")),
                }
            )
        out.sort(key=lambda x: (0 if x.get("priority") == "high" else 1, x.get("name", "")))
        return out

    async def add_watch_company(
        self,
        user_id: UUID,
        *,
        name: str,
        careers_url: str = "",
        ats_host: str = "",
        priority: str = "normal",
        notes: str = "",
    ) -> Dict[str, Any]:
        name = (name or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="Company name is required")
        entity = await self.kb.create(
            user_id,
            WikiEntityCreate(
                entity_type=ENTITY_TYPE_WATCH,
                title=name[:120],
                content={
                    "name": name,
                    "careers_url": (careers_url or "").strip(),
                    "ats_host": (ats_host or "").strip(),
                    "priority": priority if priority in ("high", "normal", "low") else "normal",
                    "notes": (notes or "").strip(),
                },
            ),
        )
        return {
            "id": str(entity.id),
            "name": entity.title,
            **(entity.content or {}),
        }

    async def remove_watch_company(self, user_id: UUID, entity_id: UUID) -> Dict[str, Any]:
        entities = await self.kb.get_by_user_id(user_id)
        target = next((e for e in entities if e.id == entity_id), None)
        if not target or target.entity_type != ENTITY_TYPE_WATCH:
            raise HTTPException(status_code=404, detail="Watchlist company not found")
        await self.db.delete(target)
        await self.db.commit()
        return {"removed": str(entity_id)}

    async def seed_example_watchlist(self, user_id: UUID) -> Dict[str, Any]:
        """Seed a few ATS-friendly examples when watchlist is empty."""
        existing = await self.list_watchlist(user_id)
        if existing:
            return {"seeded": 0, "watchlist": existing}
        examples = [
            {
                "name": "Stripe",
                "careers_url": "https://boards.greenhouse.io/stripe",
                "ats_host": "greenhouse.io",
                "priority": "high",
            },
            {
                "name": "Figma",
                "careers_url": "https://boards.greenhouse.io/figma",
                "ats_host": "greenhouse.io",
                "priority": "normal",
            },
            {
                "name": "Notion",
                "careers_url": "https://jobs.ashbyhq.com/notion",
                "ats_host": "ashbyhq.com",
                "priority": "normal",
            },
        ]
        created = 0
        for ex in examples:
            await self.add_watch_company(user_id, **ex)
            created += 1
        return {"seeded": created, "watchlist": await self.list_watchlist(user_id)}

    def get_schedule(self, user_id: UUID) -> Dict[str, Any]:
        path = _user_schedule_path(user_id)
        base = self.default_schedule()
        if not path.exists():
            return base
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            merged = {**base, **data}
            merged["preferences"] = {**base["preferences"], **(data.get("preferences") or {})}
            return merged
        except Exception as exc:
            logger.warning("Corrupt loop schedule for %s: %s", user_id, exc)
            return base

    def save_schedule(self, user_id: UUID, patch: Dict[str, Any]) -> Dict[str, Any]:
        current = self.get_schedule(user_id)
        if "enabled" in patch:
            current["enabled"] = bool(patch["enabled"])
        if "interval_hours" in patch:
            hours = int(patch["interval_hours"] or 24)
            current["interval_hours"] = max(1, min(168, hours))
        if "watchlist_only" in patch:
            current["watchlist_only"] = bool(patch["watchlist_only"])
        if "resume_refresh_hint" in patch:
            current["resume_refresh_hint"] = bool(patch["resume_refresh_hint"])
        if "auto_build_packets" in patch:
            current["auto_build_packets"] = bool(patch["auto_build_packets"])
        if "notify_email" in patch:
            current["notify_email"] = bool(patch["notify_email"])
        if isinstance(patch.get("preferences"), dict):
            current["preferences"] = {**current["preferences"], **patch["preferences"]}
        path = _user_schedule_path(user_id)
        path.write_text(json.dumps(current, indent=2), encoding="utf-8")
        return current

    async def build_scan_preferences(self, user_id: UUID) -> Dict[str, Any]:
        from app.application.services.apply_prefs import ApplyPrefsService

        schedule = self.get_schedule(user_id)
        prefs = dict(schedule.get("preferences") or {})
        apply_prefs = await ApplyPrefsService(self.db).get(user_id)
        if not str(prefs.get("workAuthorization") or "").strip():
            prefs["workAuthorization"] = str(
                apply_prefs.get("work_authorization") or ""
            ).strip()
        watchlist = await self.list_watchlist(user_id)
        if schedule.get("watchlist_only") and watchlist:
            prefs["watchlistOnly"] = True
            prefs["watchlistCompanies"] = [w["name"] for w in watchlist if w.get("name")]
        elif watchlist:
            prefs["watchlistCompanies"] = [w["name"] for w in watchlist if w.get("name")]
        prefs["loopEngineer"] = True
        return prefs

    def _is_due(self, schedule: Dict[str, Any]) -> bool:
        if not schedule.get("enabled"):
            return False
        last = schedule.get("last_run_at")
        if not last:
            return True
        try:
            last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
        except Exception:
            return True
        interval = timedelta(hours=int(schedule.get("interval_hours") or 24))
        return _utc_now() >= last_dt + interval

    def _record_run(
        self,
        user_id: UUID,
        *,
        run_id: Optional[str],
        job_count: int,
        error: Optional[str] = None,
    ) -> None:
        schedule = self.get_schedule(user_id)
        schedule["last_run_at"] = _utc_now_iso()
        schedule["last_run_id"] = run_id
        schedule["last_run_jobs"] = job_count
        schedule["last_error"] = error
        _user_schedule_path(user_id).write_text(
            json.dumps(schedule, indent=2), encoding="utf-8"
        )

    async def run_scan(
        self,
        user_id: UUID,
        *,
        trigger: str = "manual",
    ) -> Dict[str, Any]:
        """Run Search Pipeline scan; stops at awaiting_shortlist."""
        from app.application.services.search_pipeline import SearchPipelineService
        from app.infrastructure.llm.client import warm_ollama_model
        from app.infrastructure.llm.runtime import get_llm_runtime

        runtime = get_llm_runtime()
        if runtime.provider == "ollama":
            try:
                await warm_ollama_model()
            except Exception as exc:
                logger.warning("Ollama warm before loop scan: %s", exc)

        prefs = await self.build_scan_preferences(user_id)
        pipeline = SearchPipelineService(self.db)
        try:
            run = await pipeline.start_scan(user_id, prefs)
            run["trigger"] = trigger
            run["loop_engineer"] = True
            pipeline._save(user_id, run)
            job_count = len(run.get("jobs") or [])
            self._record_run(user_id, run_id=run.get("id"), job_count=job_count)

            schedule = self.get_schedule(user_id)
            packets_built: list = []
            notify_result: dict = {}
            if schedule.get("auto_build_packets", True) and job_count > 0:
                from app.application.services.job_packet import JobPacketService
                from app.application.services.loop_notify import LoopNotifyService

                pkt_svc = JobPacketService(self.db)
                packets_built = await pkt_svc.build_packets_for_run(user_id, run)
                notify_result = await LoopNotifyService(self.db).notify_packets_ready(
                    user_id,
                    run_id=run.get("id"),
                    schedule=schedule,
                    frontend_base=getattr(
                        self.settings, "LOOP_ENGINEER_FRONTEND_URL", "http://localhost:3000"
                    ),
                )

            pending_packets = len(
                [p for p in packets_built if p.get("status") == "pending_review"]
            )
            msg = f"Found {job_count} role(s)."
            if pending_packets:
                msg += (
                    f" Built {pending_packets} research packet(s) — review in /loop "
                    f"before confirming apply."
                )
            else:
                msg += " Approve shortlist in Pipeline to continue."

            return {
                "ok": True,
                "run_id": run.get("id"),
                "stage": run.get("stage"),
                "job_count": job_count,
                "packets_built": len(packets_built),
                "packets_pending_review": pending_packets,
                "notify": notify_result,
                "sources_used": run.get("sources_used") or [],
                "llm_provider": runtime.provider,
                "llm_model": runtime.model,
                "message": msg,
            }
        except Exception as exc:
            logger.exception("Loop Engineer scan failed for user %s", user_id)
            self._record_run(user_id, run_id=None, job_count=0, error=str(exc))
            raise HTTPException(
                status_code=502,
                detail=f"Loop Engineer scan failed: {type(exc).__name__}: {exc}",
            ) from exc

    def digest_lines(self, user_id: UUID) -> List[Dict[str, Any]]:
        """Pipeline runs + job packets needing attention for Inbox digest."""
        from app.application.services.search_pipeline import SearchPipelineService
        from app.application.services.job_packet import JobPacketService

        lines: List[Dict[str, Any]] = []
        pkt_svc = JobPacketService(self.db)
        pending_packets = pkt_svc.list_packets(user_id, status="pending_review", limit=10)
        if pending_packets:
            lines.append(
                {
                    "text": (
                        f"{len(pending_packets)} job packet(s) ready — "
                        f"review company research + tailored resume in Loop Engineer."
                    ),
                    "href": "/loop",
                    "run_id": pending_packets[0].get("run_id"),
                    "stage": "packets_pending",
                }
            )

        svc = SearchPipelineService(self.db)
        runs = svc.list_runs(user_id, limit=5)
        pending = [
            r
            for r in runs
            if r.get("stage") in ("awaiting_shortlist", "awaiting_evaluate", "awaiting_execute")
        ]
        for r in pending:
            stage = r.get("stage") or ""
            label = {
                "awaiting_shortlist": "shortlist approval",
                "awaiting_evaluate": "evaluate approval",
                "awaiting_execute": "apply/email approval",
            }.get(stage, stage)
            lines.append(
                {
                    "text": (
                        f"Pipeline run has {r.get('job_count', 0)} job(s) — "
                        f"needs {label}."
                    ),
                    "href": f"/pipeline?run_id={r.get('id')}",
                    "run_id": r.get("id"),
                    "stage": stage,
                }
            )

        schedule = self.get_schedule(user_id)
        if schedule.get("enabled"):
            last = schedule.get("last_run_at")
            if last:
                lines.append(
                    {
                        "text": (
                            f"Loop Engineer last scan: {schedule.get('last_run_jobs', 0)} "
                            f"job(s) at {str(last)[:16].replace('T', ' ')} UTC."
                        ),
                        "href": "/loop",
                        "run_id": schedule.get("last_run_id"),
                        "stage": "schedule",
                    }
                )
            if schedule.get("last_error"):
                lines.append(
                    {
                        "text": f"Loop Engineer scan error: {schedule['last_error'][:120]}",
                        "href": "/loop",
                        "run_id": None,
                        "stage": "error",
                    }
                )
        return lines

    async def status(self, user_id: UUID) -> Dict[str, Any]:
        from app.infrastructure.llm.runtime import runtime_status

        watchlist = await self.list_watchlist(user_id)
        schedule = self.get_schedule(user_id)
        digest = self.digest_lines(user_id)
        from app.application.services.job_packet import JobPacketService

        packets = JobPacketService(self.db).list_packets(user_id, limit=20)
        llm = runtime_status()
        return {
            "watchlist": watchlist,
            "watchlist_count": len(watchlist),
            "schedule": schedule,
            "due": self._is_due(schedule),
            "digest": digest,
            "packets": packets,
            "packets_pending": len([p for p in packets if p.get("status") == "pending_review"]),
            "llm": llm,
            "recommended_models": {
                "ollama": ["qwen2.5:3b", "deepseek-r1:1.5b"],
                "tokenharbor_free": ["kimi-k3:free", "deepseek-v4-flash:free"],
            },
        }

    @staticmethod
    async def list_scheduled_user_ids() -> List[UUID]:
        """Users with a schedule file and enabled=true."""
        ids: List[UUID] = []
        root = _loop_root()
        for path in root.glob("*/schedule.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not data.get("enabled"):
                    continue
                ids.append(UUID(path.parent.name))
            except Exception:
                continue
        return ids

    @classmethod
    async def tick(cls) -> Dict[str, Any]:
        """Background tick — run due scans for all enabled schedules."""
        if not getattr(get_settings(), "LOOP_ENGINEER_ENABLED", True):
            return {"skipped": True, "reason": "LOOP_ENGINEER_ENABLED=false"}

        from app.infrastructure.db.session import async_session

        results: List[Dict[str, Any]] = []
        user_ids = await cls.list_scheduled_user_ids()
        for user_id in user_ids:
            async with async_session() as db:
                svc = cls(db)
                schedule = svc.get_schedule(user_id)
                if not svc._is_due(schedule):
                    results.append({"user_id": str(user_id), "status": "not_due"})
                    continue
                try:
                    out = await svc.run_scan(user_id, trigger="scheduled")
                    results.append(
                        {
                            "user_id": str(user_id),
                            "status": "ok",
                            "run_id": out.get("run_id"),
                            "job_count": out.get("job_count"),
                        }
                    )
                except HTTPException as exc:
                    results.append(
                        {
                            "user_id": str(user_id),
                            "status": "error",
                            "detail": exc.detail,
                        }
                    )
                except Exception as exc:
                    results.append(
                        {
                            "user_id": str(user_id),
                            "status": "error",
                            "detail": str(exc),
                        }
                    )
        logger.info("Loop Engineer tick: %d users, results=%s", len(user_ids), results)
        return {"users_checked": len(user_ids), "results": results}
