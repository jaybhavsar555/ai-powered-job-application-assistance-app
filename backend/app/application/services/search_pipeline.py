"""
Approval-gated Search Pipeline (career-ops + ai-job-search inspired).

Stages (nothing applies or emails without an explicit approve):
  scan → awaiting_shortlist → evaluate → awaiting_evaluate
  → prepare → awaiting_execute → execute → done

Persistence is file-backed under SEARCH_PIPELINE_DIR (no DB migration).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings

logger = logging.getLogger(__name__)

STAGES = [
    {
        "id": "scan",
        "title": "Scan portals & web",
        "desc": "Search Knowledge Vault portals, common boards, and open web.",
        "needs_approval": False,
    },
    {
        "id": "awaiting_shortlist",
        "title": "Approve shortlist",
        "desc": "Pick which roles to evaluate — discard the rest.",
        "needs_approval": True,
    },
    {
        "id": "evaluate",
        "title": "Evaluate fit",
        "desc": "Score shortlisted roles (skills, experience, logistics).",
        "needs_approval": False,
    },
    {
        "id": "awaiting_evaluate",
        "title": "Approve to prepare",
        "desc": "Confirm which evaluated roles get packages and email drafts.",
        "needs_approval": True,
    },
    {
        "id": "prepare",
        "title": "Prepare docs & drafts",
        "desc": "Wishlist ingest, apply package notes, outreach email drafts.",
        "needs_approval": False,
    },
    {
        "id": "awaiting_execute",
        "title": "Approve apply / email",
        "desc": "Per job: allow Review & Apply and/or send outreach email.",
        "needs_approval": True,
    },
    {
        "id": "execute",
        "title": "Execute approved actions",
        "desc": "Start apply sessions and queue approved emails (no silent submit).",
        "needs_approval": False,
    },
    {
        "id": "done",
        "title": "Done",
        "desc": "Pipeline finished. Continue in Apply, Outreach, or Tracker.",
        "needs_approval": False,
    },
]

STAGE_IDS = [s["id"] for s in STAGES]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pipeline_root() -> Path:
    settings = get_settings()
    root = Path(getattr(settings, "SEARCH_PIPELINE_DIR", None) or "./data/pipelines")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _user_dir(user_id: UUID) -> Path:
    d = _pipeline_root() / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def _run_path(user_id: UUID, run_id: str) -> Path:
    return _user_dir(user_id) / f"{run_id}.json"


class SearchPipelineService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def list_runs(self, user_id: UUID, limit: int = 20) -> List[Dict[str, Any]]:
        files = sorted(
            _user_dir(user_id).glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        out: List[Dict[str, Any]] = []
        for path in files[:limit]:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                out.append(
                    {
                        "id": data.get("id"),
                        "stage": data.get("stage"),
                        "created_at": data.get("created_at"),
                        "updated_at": data.get("updated_at"),
                        "job_count": len(data.get("jobs") or []),
                        "preferences": data.get("preferences") or {},
                    }
                )
            except Exception as exc:
                logger.warning("Skip corrupt pipeline file %s: %s", path, exc)
        return out

    def get_run(self, user_id: UUID, run_id: str) -> Dict[str, Any]:
        path = _run_path(user_id, run_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Pipeline run not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, user_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        data["updated_at"] = _utc_now()
        path = _run_path(user_id, data["id"])
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def stages_meta(self) -> List[Dict[str, Any]]:
        return list(STAGES)

    async def start_scan(
        self,
        user_id: UUID,
        preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Stage 1: scan Vault + boards + web, score, then wait for shortlist approval."""
        from app.application.agents.job_discovery_agent import JobDiscoveryAgent
        from app.application.services.knowledge import KnowledgeBaseService

        knowledge = KnowledgeBaseService(self.db)
        try:
            await knowledge.seed_job_portals(user_id)
        except Exception as seed_exc:
            logger.warning("Vault seed during pipeline scan: %s", seed_exc)

        agent = JobDiscoveryAgent(knowledge_service=knowledge)
        jobs = await agent.discover_and_score_jobs(str(user_id), preferences)

        run_id = str(uuid4())
        items = []
        for j in jobs:
            items.append(
                {
                    **j,
                    "shortlisted": False,
                    "evaluate_approved": False,
                    "evaluation": None,
                    "prepared": False,
                    "ingested_job_id": None,
                    "application_id": None,
                    "email_draft": None,
                    "approve_apply": False,
                    "approve_email": False,
                    "apply_session_id": None,
                    "email_status": None,
                    "execute_notes": [],
                }
            )

        sources_used = sorted(
            {str(j.get("source") or "unknown") for j in jobs if j.get("source")}
        )
        data: Dict[str, Any] = {
            "id": run_id,
            "user_id": str(user_id),
            "stage": "awaiting_shortlist" if items else "done",
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
            "preferences": preferences,
            "sources_used": sources_used,
            "jobs": items,
            "history": [
                {
                    "at": _utc_now(),
                    "stage": "scan",
                    "detail": f"Found {len(items)} jobs from {', '.join(sources_used) or 'none'}.",
                }
            ],
            "philosophy": (
                "Inspired by career-ops and ai-job-search: draft and prepare freely, "
                "never apply or send email without your approval at each gate."
            ),
        }
        return self._save(user_id, data)

    def approve_shortlist(
        self, user_id: UUID, run_id: str, job_ids: List[str]
    ) -> Dict[str, Any]:
        data = self.get_run(user_id, run_id)
        if data.get("stage") != "awaiting_shortlist":
            raise HTTPException(
                status_code=400,
                detail=f"Run is at stage {data.get('stage')}, expected awaiting_shortlist",
            )
        wanted = set(job_ids or [])
        if not wanted:
            raise HTTPException(
                status_code=400, detail="Select at least one job to shortlist"
            )
        for job in data.get("jobs") or []:
            job["shortlisted"] = str(job.get("id")) in wanted
        data["stage"] = "evaluate"
        data["history"].append(
            {
                "at": _utc_now(),
                "stage": "awaiting_shortlist",
                "detail": f"Shortlisted {len(wanted)} job(s).",
            }
        )
        self._save(user_id, data)
        return self._run_evaluate(user_id, data)

    def _run_evaluate(self, user_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Lightweight multi-dimension fit notes (Mads / career-ops style)."""
        for job in data.get("jobs") or []:
            if not job.get("shortlisted"):
                continue
            score = int(job.get("matchScore") or job.get("match_score") or 70)
            score = max(0, min(100, score))
            # Map 0–100 → career-ops-ish 1.0–5.0
            global_score = round(1.0 + (score / 100.0) * 4.0, 1)
            reason = str(job.get("matchReason") or job.get("match_reason") or "")
            job["evaluation"] = {
                "global_score": global_score,
                "match_score_100": score,
                "dimensions": {
                    "skills": score,
                    "experience": max(40, score - 5),
                    "logistics": 80 if "remote" in str(job.get("location") or "").lower() else 65,
                    "motivation": max(50, score - 10),
                },
                "recommendation": (
                    "Strong apply" if global_score >= 4.0 else
                    "Consider" if global_score >= 3.2 else
                    "Skip unless strategic"
                ),
                "notes": reason
                or "Scored from discovery match against your resume and prefs.",
                "legitimacy": "unverified — open the posting URL before applying",
            }
            job["evaluate_approved"] = False

        data["stage"] = "awaiting_evaluate"
        data["history"].append(
            {
                "at": _utc_now(),
                "stage": "evaluate",
                "detail": "Fit evaluation ready for approval.",
            }
        )
        return self._save(user_id, data)

    async def approve_evaluate(
        self, user_id: UUID, run_id: str, job_ids: List[str]
    ) -> Dict[str, Any]:
        data = self.get_run(user_id, run_id)
        if data.get("stage") != "awaiting_evaluate":
            raise HTTPException(
                status_code=400,
                detail=f"Run is at stage {data.get('stage')}, expected awaiting_evaluate",
            )
        wanted = set(job_ids or [])
        if not wanted:
            raise HTTPException(
                status_code=400, detail="Select at least one job to prepare"
            )
        for job in data.get("jobs") or []:
            if str(job.get("id")) in wanted and job.get("shortlisted"):
                job["evaluate_approved"] = True
            else:
                job["evaluate_approved"] = False
        data["stage"] = "prepare"
        data["history"].append(
            {
                "at": _utc_now(),
                "stage": "awaiting_evaluate",
                "detail": f"Approved {len(wanted)} job(s) for prepare.",
            }
        )
        self._save(user_id, data)
        return await self._run_prepare(user_id, data)

    async def _run_prepare(
        self, user_id: UUID, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        from app.application.services.job import JobService
        from app.schemas.job import JobCreate
        from app.infrastructure.db.models import DBApplication
        from sqlalchemy.future import select

        job_service = JobService(self.db)
        prepared = 0
        for job in data.get("jobs") or []:
            if not job.get("evaluate_approved"):
                continue
            url = (job.get("url") or "").strip() or None
            desc = (job.get("full_jd") or job.get("description") or "").strip()
            title = (job.get("title") or "Open Role").strip()
            company = (job.get("company") or job.get("company_name") or "").strip()
            # Ensure enough text for ingest when scrape would fail
            raw = desc if len(desc) >= 80 else (
                f"{title} at {company or 'Company'}.\n\n"
                f"{desc}\n\n"
                f"Source URL: {url or 'n/a'}\n"
                f"Discovered via Career OS Search Pipeline.\n"
                + ("x" * max(0, 80 - len(desc)))
            )
            try:
                db_job = await job_service.ingest_job(
                    user_id,
                    JobCreate(
                        url=url,
                        role_title=title,
                        company_name=company or None,
                        description_raw=raw,
                    ),
                )
                job["ingested_job_id"] = str(db_job.id)
                result = await self.db.execute(
                    select(DBApplication).where(
                        DBApplication.user_id == user_id,
                        DBApplication.job_id == db_job.id,
                    )
                )
                app = result.scalars().first()
                if app:
                    job["application_id"] = str(app.id)
            except HTTPException as exc:
                job["execute_notes"] = list(job.get("execute_notes") or [])
                job["execute_notes"].append(f"Ingest skipped: {exc.detail}")
            except Exception as exc:
                logger.exception("Pipeline prepare ingest failed")
                job["execute_notes"] = list(job.get("execute_notes") or [])
                job["execute_notes"].append(f"Ingest error: {exc}")

            job["email_draft"] = {
                "subject": f"Interest in {title} — {company or 'your team'}",
                "body": (
                    f"Hi,\n\n"
                    f"I came across the {title} role"
                    f"{f' at {company}' if company else ''} and believe my background "
                    f"is a strong fit.\n\n"
                    f"I'd welcome a brief conversation about the role and how I can help.\n\n"
                    f"Best regards\n"
                ),
                "to": None,
                "status": "draft",
                "note": "Draft only — send requires your approve_email on the next gate.",
            }
            job["prepared"] = True
            job["approve_apply"] = False
            job["approve_email"] = False
            prepared += 1

        data["stage"] = "awaiting_execute"
        data["history"].append(
            {
                "at": _utc_now(),
                "stage": "prepare",
                "detail": f"Prepared {prepared} job(s) — awaiting execute approvals.",
            }
        )
        return self._save(user_id, data)

    async def approve_execute(
        self,
        user_id: UUID,
        run_id: str,
        actions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        actions: [{ "job_id": "...", "approve_apply": true, "approve_email": true }]
        """
        data = self.get_run(user_id, run_id)
        if data.get("stage") != "awaiting_execute":
            raise HTTPException(
                status_code=400,
                detail=f"Run is at stage {data.get('stage')}, expected awaiting_execute",
            )
        if not actions:
            raise HTTPException(
                status_code=400, detail="Provide at least one per-job action approval"
            )

        by_id = {a.get("job_id"): a for a in actions if a.get("job_id")}
        any_flag = False
        for job in data.get("jobs") or []:
            act = by_id.get(str(job.get("id")))
            if not act or not job.get("prepared"):
                continue
            job["approve_apply"] = bool(act.get("approve_apply"))
            job["approve_email"] = bool(act.get("approve_email"))
            if job["approve_apply"] or job["approve_email"]:
                any_flag = True

        if not any_flag:
            raise HTTPException(
                status_code=400,
                detail="Enable apply and/or email on at least one prepared job",
            )

        data["stage"] = "execute"
        data["history"].append(
            {
                "at": _utc_now(),
                "stage": "awaiting_execute",
                "detail": "Execute approvals recorded.",
            }
        )
        self._save(user_id, data)
        return await self._run_execute(user_id, data)

    async def _run_execute(
        self, user_id: UUID, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        from app.application.services.apply_session import ApplySessionService
        from app.application.services.mail import MailService
        from app.infrastructure.db.models import DBMessage, DBApplication
        from sqlalchemy.future import select
        from urllib.parse import quote

        apply_svc = ApplySessionService(self.db)
        mail = MailService()

        for job in data.get("jobs") or []:
            notes = list(job.get("execute_notes") or [])

            if job.get("approve_apply") and job.get("ingested_job_id"):
                try:
                    session = await apply_svc.start(
                        user_id,
                        job_id=UUID(str(job["ingested_job_id"])),
                    )
                    job["apply_session_id"] = str(session.get("id") or "")
                    notes.append(
                        "Review & Apply session started — complete gates in /apply "
                        "(no silent board submit)."
                    )
                except Exception as exc:
                    logger.exception("Pipeline apply session failed")
                    notes.append(f"Apply session failed: {exc}")

            if job.get("approve_email") and job.get("email_draft"):
                draft = dict(job["email_draft"])
                to_addr = (draft.get("to") or "").strip()
                content = (
                    f"Subject: {draft.get('subject') or ''}\n\n{draft.get('body') or ''}"
                )
                app_id = job.get("application_id")
                if app_id:
                    try:
                        result = await self.db.execute(
                            select(DBApplication).where(
                                DBApplication.id == UUID(str(app_id))
                            )
                        )
                        app = result.scalars().first()
                        if app:
                            msg = DBMessage(
                                application_id=app.id,
                                content=content,
                                message_type="Email",
                                status="Draft",
                            )
                            self.db.add(msg)
                            await self.db.flush()
                            draft["message_id"] = str(msg.id)
                            draft["status"] = "draft_saved"
                            notes.append(
                                "Email saved as Outreach draft — open /outreach to edit and send."
                            )
                            # Only SMTP-send when recipient is set AND SMTP configured
                            if to_addr and mail.smtp_configured:
                                try:
                                    ok = mail.send_email(
                                        to_addr,
                                        draft.get("subject") or "",
                                        draft.get("body") or "",
                                    )
                                    if ok:
                                        msg.status = "Sent"
                                        draft["status"] = "sent"
                                        notes.append(f"Email sent via SMTP to {to_addr}.")
                                except Exception as send_exc:
                                    notes.append(
                                        f"SMTP not sent ({send_exc}); use Outreach mailto."
                                    )
                    except Exception as exc:
                        logger.exception("Pipeline email draft failed")
                        notes.append(f"Email draft failed: {exc}")
                else:
                    draft["status"] = "draft_local"
                    subj = quote(draft.get("subject") or "")
                    body_q = quote(draft.get("body") or "")
                    draft["mailto"] = f"mailto:{to_addr or ''}?subject={subj}&body={body_q}"
                    notes.append(
                        "No application row — email kept on pipeline run; "
                        "copy body or add contact in Outreach after Wishlist."
                    )
                job["email_draft"] = draft
                job["email_status"] = draft.get("status")

            job["execute_notes"] = notes

        await self.db.commit()
        data["stage"] = "done"
        data["history"].append(
            {
                "at": _utc_now(),
                "stage": "execute",
                "detail": "Approved actions executed. Finish apply gates / send from Outreach.",
            }
        )
        return self._save(user_id, data)
