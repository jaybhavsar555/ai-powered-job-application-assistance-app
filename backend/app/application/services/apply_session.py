"""
Optim Hire–style Review & Apply session.

Human approval at each gate. We prepare data and showcase form fill steps;
actual board submit is confirmed by the user (no fake silent auto-apply).
"""

from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.infrastructure.db.models import DBApplication, DBJob, DBUser
from app.infrastructure.resume_library import (
    detect_role_family,
    extract_text,
    list_resume_files,
    parse_contact,
    pick_base_resume,
)
from app.core.config import get_settings
from app.application.services.follow_up import schedule_follow_up_on_applied

STEP_DEFS = [
    {
        "id": "review_match",
        "title": "Review job match",
        "desc": "Confirm this JD fits your preferences before we proceed.",
        "needs_approval": True,
        "showcase": "match",
    },
    {
        "id": "prepare_docs",
        "title": "Prepare resume & cover",
        "desc": "Use Canvas-tailored docs or your master resume for this role.",
        "needs_approval": True,
        "showcase": "docs",
    },
    {
        "id": "open_site",
        "title": "Open employer site",
        "desc": "We open the job posting so you can see the real application form.",
        "needs_approval": True,
        "showcase": "browser",
    },
    {
        "id": "fill_form",
        "title": "Fill application form",
        "desc": "We map your profile into typical form fields — you approve each batch.",
        "needs_approval": True,
        "showcase": "form_fill",
    },
    {
        "id": "attach_resume",
        "title": "Attach resume / package",
        "desc": "Upload the generated PDF/DOCX on the employer form.",
        "needs_approval": True,
        "showcase": "attach",
    },
    {
        "id": "submit_confirm",
        "title": "Confirm you submitted",
        "desc": "Click Submit on their site, then confirm here — we mark Applied + queue follow-up.",
        "needs_approval": True,
        "showcase": "submit",
    },
]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _company(job: Optional[DBJob]) -> str:
    if not job:
        return "Unknown"
    if job.company and job.company.name:
        return job.company.name
    return str((job.description_normalized or {}).get("company_name") or "Unknown")


def _display_role(job: Optional[DBJob]) -> Optional[str]:
    if not job:
        return None
    title = (job.role_title or "").strip()
    normalized = job.description_normalized or {}
    alt = str(
        normalized.get("role_title")
        or normalized.get("title")
        or normalized.get("position")
        or ""
    ).strip()

    def _looks_like_role(t: str) -> bool:
        if not t or len(t) > 80:
            return False
        low = t.lower()
        fluff = (
            "great to see",
            "work together",
            "join us",
            "we're hiring",
            "apply now",
            "thank you",
        )
        if any(x in low for x in fluff):
            return False
        return True

    if _looks_like_role(title):
        return title
    if _looks_like_role(alt):
        return alt
    return None


def _name_from_email(email: str) -> str:
    local = (email or "").split("@")[0]
    parts = [p for p in re.split(r"[._+\-]+", local) if p and not p.isdigit()]
    # Drop common junk tokens
    skip = {"dev", "mail", "hello", "hi", "contact"}
    parts = [p for p in parts if p.lower() not in skip]
    if not parts:
        return "Candidate"
    return " ".join(p.capitalize() for p in parts[:4])


class ApplySessionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    def _save_session(self, app: DBApplication, session: dict[str, Any]) -> None:
        state = copy.deepcopy(dict(app.workflow_state or {}))
        state["apply_session"] = copy.deepcopy(session)
        app.workflow_state = state
        flag_modified(app, "workflow_state")

    async def _load_app(self, user_id: UUID, application_id: UUID) -> DBApplication:
        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.id == application_id, DBApplication.user_id == user_id)
            .options(
                selectinload(DBApplication.job).selectinload(DBJob.company),
            )
        )
        app = result.scalars().first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        return app

    def _docs_payload(self, state: dict[str, Any], job: Optional[DBJob]) -> dict[str, Any]:
        package = state.get("apply_package") or state.get("package") or {}
        if not isinstance(package, dict):
            package = {}
        tailored = state.get("tailored_resume") or {}
        cover = state.get("cover_letter") or ""
        if isinstance(cover, dict):
            cover = cover.get("content") or cover.get("body") or ""
        matching = state.get("matching_skills") or []
        missing = state.get("missing_skills") or []
        ats = state.get("ats_score")
        return {
            "ats_score": ats,
            "matching_skills": matching[:8] if isinstance(matching, list) else [],
            "missing_skills": missing[:8] if isinstance(missing, list) else [],
            "has_tailored_resume": bool(tailored),
            "has_cover_letter": bool(str(cover).strip()),
            "cover_letter_preview": (str(cover).strip()[:480] + ("…" if len(str(cover).strip()) > 480 else ""))
            if cover
            else None,
            "package": package or None,
            "package_ready": bool(package.get("folder") or package.get("files")),
            "canvas_href": f"/canvas?job_id={job.id}" if job else "/canvas",
            "approvals_href": "/approvals",
            "jobs_href": "/jobs",
            "hint": (
                "Docs ready — approve this step, then open the employer site."
                if package or tailored or cover
                else "No tailored package yet. Open Canvas to generate resume/cover, or approve to continue with your master resume."
            ),
        }

    async def _profile_fields(self, user: DBUser, job: Optional[DBJob]) -> list[dict[str, Any]]:
        name = _name_from_email(user.email)
        email = user.email
        phone = ""
        location = ""
        linkedin = ""

        try:
            source = Path(self.settings.RESUME_SOURCE_DIR) if self.settings.RESUME_SOURCE_DIR else None
            if source and source.exists():
                role_title = job.role_title if job else ""
                jd = (job.description_raw or "") if job else ""
                family = detect_role_family(role_title or "", jd)
                base = pick_base_resume(source, family)
                if base:
                    text = extract_text(base.path)
                    parsed_name, contact = parse_contact(text)
                    if parsed_name and parsed_name.lower() != "candidate":
                        name = parsed_name
                    parts = [
                        p.strip()
                        for p in (contact or "").replace("|", ",").split(",")
                        if p.strip()
                    ]
                    for p in parts:
                        if "@" in p:
                            email = p
                        elif re.search(r"\d{8,}", re.sub(r"\D", "", p)) or any(
                            c.isdigit() for c in p
                        ):
                            if sum(c.isdigit() for c in p) >= 8:
                                phone = p
                        elif "linkedin.com" in p.lower():
                            linkedin = p
                        elif not location and len(p) < 60:
                            location = p
        except Exception:
            pass

        if not location and job:
            location = str((job.description_normalized or {}).get("location") or "")

        return [
            {"key": "full_name", "label": "Full name", "value": name, "status": "ready"},
            {"key": "email", "label": "Email", "value": email, "status": "ready"},
            {
                "key": "phone",
                "label": "Phone",
                "value": phone or "Add on form if required",
                "status": "ready" if phone else "manual",
            },
            {
                "key": "linkedin",
                "label": "LinkedIn / portfolio",
                "value": linkedin or "Paste from Vault / profile if asked",
                "status": "ready" if linkedin else "manual",
            },
            {
                "key": "location",
                "label": "Location / work auth",
                "value": location or "Confirm on form",
                "status": "review" if location else "manual",
            },
            {
                "key": "work_auth",
                "label": "Work authorization",
                "value": "Answer honestly on their form (see Screening Q&A)",
                "status": "manual",
            },
            {
                "key": "salary",
                "label": "Salary expectation",
                "value": "Optional — use your range if asked",
                "status": "manual",
            },
        ]

    def _serialize(self, app: DBApplication, session: dict[str, Any]) -> dict[str, Any]:
        job = app.job
        state = app.workflow_state or {}
        return {
            "session_id": session["id"],
            "application_id": str(app.id),
            "job_id": str(app.job_id),
            "mode": "review_and_apply",
            "mode_note": (
                "Like Optim Hire Review & Apply: we prepare fields and walk the form; "
                "you approve each step and click Submit on the employer site."
            ),
            "status": session.get("status", "active"),
            "current_step_index": session.get("current_step_index", 0),
            "company": _company(job),
            "role_title": _display_role(job),
            "job_url": job.url if job else None,
            "steps": session.get("steps", []),
            "form_fields": session.get("form_fields", []),
            "package": session.get("package"),
            "docs": session.get("docs") or self._docs_payload(state, job),
            "browser": session.get("browser", {}),
            "updated_at": session.get("updated_at"),
        }

    def _ensure_step_statuses(self, session: dict[str, Any]) -> None:
        """Keep one active step aligned with current_step_index."""
        steps = list(session.get("steps") or [])
        if not steps:
            return
        idx = int(session.get("current_step_index", 0))
        idx = max(0, min(idx, len(steps) - 1))
        for i, step in enumerate(steps):
            if step.get("status") == "approved":
                continue
            step["status"] = "active" if i == idx else "pending"
        session["current_step_index"] = idx
        session["steps"] = steps

    async def start(
        self,
        user_id: UUID,
        *,
        application_id: Optional[UUID] = None,
        job_id: Optional[UUID] = None,
        reset: bool = False,
    ) -> dict[str, Any]:
        if not application_id and not job_id:
            raise HTTPException(status_code=400, detail="Provide application_id or job_id")

        if application_id:
            app = await self._load_app(user_id, application_id)
        else:
            result = await self.db.execute(
                select(DBApplication)
                .where(DBApplication.user_id == user_id, DBApplication.job_id == job_id)
                .options(
                    selectinload(DBApplication.job).selectinload(DBJob.company),
                )
            )
            app = result.scalars().first()
            if not app:
                raise HTTPException(
                    status_code=404,
                    detail="No application for this job — wishlist it first",
                )

        user = await self.db.get(DBUser, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        state = copy.deepcopy(dict(app.workflow_state or {}))
        existing = state.get("apply_session")
        form_fields = await self._profile_fields(user, app.job)
        docs = self._docs_payload(state, app.job)

        if (
            not reset
            and isinstance(existing, dict)
            and existing.get("status") in ("active", "awaiting_submit_confirm")
            and existing.get("steps")
        ):
            self._ensure_step_statuses(existing)
            existing["form_fields"] = form_fields
            existing["docs"] = docs
            existing["package"] = docs.get("package")
            existing["updated_at"] = _utc_now().isoformat()
            self._save_session(app, existing)
            await self.db.commit()
            await self.db.refresh(app)
            return self._serialize(app, existing)

        steps = []
        for i, defn in enumerate(STEP_DEFS):
            steps.append(
                {
                    **defn,
                    "index": i,
                    "status": "active" if i == 0 else "pending",
                    "approved_at": None,
                }
            )

        session = {
            "id": str(uuid4()),
            "status": "active",
            "current_step_index": 0,
            "steps": steps,
            "form_fields": form_fields,
            "package": docs.get("package"),
            "docs": docs,
            "browser": {
                "opened": False,
                "url": app.job.url if app.job else None,
                "fill_progress": 0,
                "last_action": None,
            },
            "created_at": _utc_now().isoformat(),
            "updated_at": _utc_now().isoformat(),
        }
        self._save_session(app, session)
        await self.db.commit()
        await self.db.refresh(app)
        return self._serialize(app, session)

    async def get(self, user_id: UUID, application_id: UUID) -> dict[str, Any]:
        app = await self._load_app(user_id, application_id)
        session = (app.workflow_state or {}).get("apply_session")
        if not session:
            raise HTTPException(status_code=404, detail="No apply session — start one first")
        return self._serialize(app, session)

    async def approve_step(
        self,
        user_id: UUID,
        application_id: UUID,
        *,
        step_id: Optional[str] = None,
    ) -> dict[str, Any]:
        app = await self._load_app(user_id, application_id)
        state = copy.deepcopy(dict(app.workflow_state or {}))
        session = state.get("apply_session")
        if not session or session.get("status") not in (
            "active",
            "awaiting_submit_confirm",
        ):
            raise HTTPException(status_code=400, detail="No active apply session")

        self._ensure_step_statuses(session)
        steps = list(session.get("steps") or [])
        if not steps:
            raise HTTPException(status_code=400, detail="Session has no steps")

        # Prefer the step marked active; fall back to index
        idx = next(
            (i for i, s in enumerate(steps) if s.get("status") == "active"),
            int(session.get("current_step_index", 0)),
        )
        idx = max(0, min(idx, len(steps) - 1))
        current = steps[idx]

        if step_id:
            # Idempotent: already approved this step → return current state
            for s in steps:
                if s.get("id") == step_id and s.get("status") == "approved":
                    self._save_session(app, session)
                    await self.db.commit()
                    return self._serialize(app, session)

            if current.get("id") != step_id:
                asked_idx = next(
                    (i for i, s in enumerate(steps) if s.get("id") == step_id), None
                )
                if asked_idx is None:
                    raise HTTPException(status_code=400, detail=f"Unknown step: {step_id}")
                if asked_idx > idx:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Approve “{current.get('title')}” first",
                    )

        now = _utc_now().isoformat()
        current["status"] = "approved"
        current["approved_at"] = now
        steps[idx] = current

        browser = dict(session.get("browser") or {})
        sid = current.get("id")
        if sid == "open_site":
            job_url = (app.job.url if app.job else None) or browser.get("url")
            if not job_url:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "This job has no apply URL. Paste the portal link on Jobs "
                        "(edit/re-import), or skip apply and use Outreach only."
                    ),
                )
            browser["opened"] = True
            browser["last_action"] = "opened_job_url"
            browser["url"] = job_url
        elif sid == "fill_form":
            fields = list(session.get("form_fields") or [])
            for f in fields:
                if f.get("status") in ("ready", "review", "manual", "filling"):
                    f["status"] = "filled"
            session["form_fields"] = fields
            browser["fill_progress"] = 100
            browser["last_action"] = "mapped_form_fields"
        elif sid == "attach_resume":
            browser["last_action"] = "resume_attach_reminded"
        elif sid == "prepare_docs":
            session["docs"] = self._docs_payload(state, app.job)

        next_idx = idx + 1
        if next_idx < len(steps):
            steps[next_idx]["status"] = "active"
            session["current_step_index"] = next_idx
            session["status"] = "active"
        else:
            session["current_step_index"] = len(steps) - 1
            session["status"] = "awaiting_submit_confirm"

        session["steps"] = steps
        session["browser"] = browser
        session["updated_at"] = now
        self._save_session(app, session)
        await self.db.commit()
        await self.db.refresh(app)
        return self._serialize(app, session)

    async def simulate_fill(
        self, user_id: UUID, application_id: UUID
    ) -> dict[str, Any]:
        """Showcase progressive form-fill animation state (does not submit)."""
        app = await self._load_app(user_id, application_id)
        state = copy.deepcopy(dict(app.workflow_state or {}))
        session = state.get("apply_session")
        if not session:
            raise HTTPException(status_code=404, detail="No apply session")

        fields = list(session.get("form_fields") or [])
        browser = dict(session.get("browser") or {})
        advanced = False
        for f in fields:
            if f.get("status") == "ready":
                f["status"] = "filling"
                advanced = True
                break
            if f.get("status") == "filling":
                f["status"] = "filled"
                advanced = True
                break
        if not advanced:
            for f in fields:
                if f.get("status") in ("ready", "review", "manual"):
                    f["status"] = "filled"

        filled = sum(1 for f in fields if f.get("status") == "filled")
        total = max(len(fields), 1)
        browser["fill_progress"] = int(100 * filled / total)
        browser["last_action"] = "simulate_fill_tick"
        browser["opened"] = True

        session["form_fields"] = fields
        session["browser"] = browser
        session["updated_at"] = _utc_now().isoformat()
        self._save_session(app, session)
        await self.db.commit()
        await self.db.refresh(app)
        return self._serialize(app, session)

    async def confirm_submitted(
        self, user_id: UUID, application_id: UUID
    ) -> dict[str, Any]:
        app = await self._load_app(user_id, application_id)
        state = copy.deepcopy(dict(app.workflow_state or {}))
        session = state.get("apply_session")
        if not session:
            raise HTTPException(status_code=404, detail="No apply session")

        steps = session.get("steps") or []
        approved_ids = {s["id"] for s in steps if s.get("status") == "approved"}
        required = {"review_match", "open_site", "fill_form", "attach_resume"}
        missing = required - approved_ids
        if missing and session.get("status") == "active":
            current = steps[int(session.get("current_step_index", 0))]
            if current.get("id") != "submit_confirm":
                raise HTTPException(
                    status_code=400,
                    detail=f"Approve remaining steps first: {', '.join(sorted(missing))}",
                )

        for s in steps:
            if s.get("id") == "submit_confirm":
                s["status"] = "approved"
                s["approved_at"] = _utc_now().isoformat()

        session["steps"] = steps
        session["status"] = "completed"
        session["completed_at"] = _utc_now().isoformat()
        session["browser"] = {
            **(session.get("browser") or {}),
            "last_action": "user_confirmed_submit",
            "fill_progress": 100,
        }
        previous = app.stage
        app.stage = "Applied"
        self._save_session(app, session)
        await self.db.commit()

        follow_up = None
        if previous != "Applied":
            follow_up = await schedule_follow_up_on_applied(self.db, app)

        app = await self._load_app(user_id, application_id)
        session = (app.workflow_state or {}).get("apply_session") or session
        payload = self._serialize(app, session)
        payload["follow_up"] = follow_up
        payload["stage"] = app.stage
        return payload
