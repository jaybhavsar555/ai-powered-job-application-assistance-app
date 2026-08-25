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

    def _library_resume_text(
        self, job: Optional[DBJob]
    ) -> tuple[bool, str]:
        """Return (attached, extracted text) from the on-disk resume library."""
        try:
            source = Path(self.settings.RESUME_SOURCE_DIR) if self.settings.RESUME_SOURCE_DIR else None
            if not source or not source.exists():
                return False, ""
            role_title = job.role_title if job else ""
            jd = (job.description_raw or "") if job else ""
            family = detect_role_family(role_title or "", jd)
            base = pick_base_resume(source, family)
            if not base:
                return False, ""
            return True, extract_text(base.path)
        except Exception:
            return False, ""

    def _docs_payload(
        self,
        state: dict[str, Any],
        job: Optional[DBJob],
        *,
        resume_text: str = "",
    ) -> dict[str, Any]:
        package = state.get("apply_package") or state.get("package") or {}
        if not isinstance(package, dict):
            package = {}
        tailored = state.get("tailored_resume") or {}
        if not isinstance(tailored, dict):
            tailored = {}
        cover = state.get("cover_letter") or ""
        if isinstance(cover, dict):
            cover = cover.get("content") or cover.get("body") or ""
        matching = state.get("matching_skills") or []
        missing = state.get("missing_skills") or []
        if not isinstance(matching, list):
            matching = []
        if not isinstance(missing, list):
            missing = []
        ats = state.get("ats_score")
        normalized = (job.description_normalized or {}) if job else {}
        jd_skills = normalized.get("required_skills") or []
        if not isinstance(jd_skills, list):
            jd_skills = []
        required = [str(s) for s in (jd_skills or matching or []) if s][:16]
        if not required:
            required = [str(s) for s in matching[:12]]
        present = [s for s in required if s in matching or s.lower() in " ".join(matching).lower()]
        if matching and not present:
            present = [str(s) for s in matching[:12]]
        summary = str(tailored.get("summary") or "").strip()
        bullets = tailored.get("tailored_bullets") or tailored.get("bullets") or []
        if not isinstance(bullets, list):
            bullets = []
        resume_body = summary
        if bullets:
            resume_body = (summary + "\n\n" if summary else "") + "\n".join(
                f"• {b}" for b in bullets if b
            )
        if not resume_body and resume_text:
            resume_body = resume_text[:8000]
        keywords = tailored.get("added_keywords") or []
        cover_full = str(cover).strip()
        jd_text = ((job.description_raw or "") if job else "")[:8000]
        return {
            "ats_score": ats,
            "matching_skills": matching[:12],
            "missing_skills": missing[:12],
            "required_skills": required[:16],
            "present_skills": present[:16],
            "required_skill_count": len(required) or len(matching) + len(missing),
            "present_skill_count": len(present) or len(matching),
            "has_tailored_resume": bool(tailored),
            "has_cover_letter": bool(cover_full),
            "cover_letter": cover_full,
            "cover_letter_preview": (cover_full[:480] + ("…" if len(cover_full) > 480 else ""))
            if cover_full
            else None,
            "resume_preview": resume_body[:8000] or None,
            "added_keywords": [str(k) for k in keywords[:16]] if isinstance(keywords, list) else [],
            "job_description": jd_text or None,
            "package": package or None,
            "package_ready": bool(package.get("folder") or package.get("files")),
            "resume_download_kind": "resume_pdf" if package else None,
            "cover_download_kind": "cover_pdf" if package else None,
            "canvas_href": f"/canvas?job_id={job.id}" if job else "/canvas",
            "approvals_href": "/approvals",
            "jobs_href": "/jobs",
            "hint": (
                "Docs ready — review the form, then submit on the employer site."
                if package or tailored or cover_full
                else "No tailored package yet. Open Canvas to generate resume/cover, or continue with your master resume."
            ),
        }

    def _experience_from_resume(self, text: str) -> list[dict[str, str]]:
        """Best-effort work-history blocks for the review form (not a full parser)."""
        if not text:
            return []
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        jobs: list[dict[str, str]] = []
        month = (
            r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
            r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
            r"Dec(?:ember)?)"
        )
        date_re = re.compile(rf"{month}\s+\d{{4}}\s*[-–—]\s*(?:{month}\s+\d{{4}}|Present|Current)", re.I)
        for i, ln in enumerate(lines):
            if len(jobs) >= 6:
                break
            if "|" in ln and 8 < len(ln) < 90:
                left, right = [p.strip() for p in ln.split("|", 1)]
                nxt = lines[i + 1] if i + 1 < len(lines) else ""
                dates = nxt if date_re.search(nxt) else ""
                jobs.append(
                    {
                        "company": left[:80],
                        "title": right[:80],
                        "dates": dates[:40],
                    }
                )
            elif date_re.search(ln) and i > 0:
                prev = lines[i - 1]
                if 4 < len(prev) < 90 and not any(j["title"] == prev for j in jobs):
                    jobs.append({"company": "", "title": prev[:80], "dates": ln[:40]})
        # Dedupe
        seen: set[str] = set()
        out: list[dict[str, str]] = []
        for j in jobs:
            key = f"{j.get('company')}|{j.get('title')}".lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(j)
        return out[:5]

    async def _profile_fields(self, user: DBUser, job: Optional[DBJob]) -> list[dict[str, Any]]:
        name = _name_from_email(user.email)
        email = user.email
        phone = ""
        location = ""
        linkedin = ""
        resume_text = ""
        resume_attached = False
        work_auth = ""

        try:
            from app.application.services.apply_prefs import ApplyPrefsService

            prefs = await ApplyPrefsService(self.db).get(user.id)
            work_auth = str(prefs.get("work_authorization") or "")
        except Exception:
            work_auth = ""

        resume_attached, resume_text = self._library_resume_text(job)
        if resume_text:
            parsed_name, contact = parse_contact(resume_text)
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

        if not location and job:
            location = str((job.description_normalized or {}).get("location") or "")

        parts = [p for p in re.split(r"\s+", name.strip()) if p]
        first = parts[0] if parts else "Candidate"
        last = " ".join(parts[1:]) if len(parts) > 1 else ""
        auth_label = {
            "citizen": "Authorized — no sponsorship needed",
            "opt": "OPT / STEM-OPT",
            "needs_sponsorship": "Will need visa sponsorship",
            "other": "See Screening Q&A",
        }.get(work_auth, "Answer honestly on their form (Screening Q&A)")

        fields: list[dict[str, Any]] = [
            {
                "key": "first_name",
                "label": "First Name",
                "value": first,
                "status": "ready",
                "locked": False,
                "group": "personal",
            },
            {
                "key": "last_name",
                "label": "Last Name",
                "value": last,
                "status": "ready",
                "locked": False,
                "group": "personal",
            },
            {
                "key": "email",
                "label": "Email",
                "value": email,
                "status": "ready",
                "locked": True,
                "group": "personal",
                "hint": "Locked from your account. Change it in Profile / login email.",
            },
            {
                "key": "phone",
                "label": "Phone",
                "value": phone or "",
                "status": "ready" if phone else "manual",
                "locked": True,
                "group": "personal",
                "hint": "Locked from your resume. Edit the file in Resume Studio if needed.",
            },
            {
                "key": "resume",
                "label": "Resume",
                "value": "Resume attached" if resume_attached else "No resume in library",
                "status": "ready" if resume_attached else "manual",
                "locked": True,
                "group": "personal",
            },
            {
                "key": "linkedin",
                "label": "LinkedIn / portfolio",
                "value": linkedin,
                "status": "ready" if linkedin else "manual",
                "locked": False,
                "group": "personal",
            },
            {
                "key": "location",
                "label": "Location",
                "value": location,
                "status": "review" if location else "manual",
                "locked": False,
                "group": "personal",
            },
            {
                "key": "work_auth",
                "label": "Work authorization",
                "value": auth_label,
                "status": "ready" if work_auth else "manual",
                "locked": True,
                "group": "personal",
                "hint": "Set on Inbox → Work authorization.",
            },
        ]
        for i, exp in enumerate(self._experience_from_resume(resume_text), start=1):
            title = exp.get("title") or "Role"
            company = exp.get("company") or ""
            dates = exp.get("dates") or ""
            label = f"Work Experience {i}"
            value = " · ".join([p for p in (title, company, dates) if p])
            fields.append(
                {
                    "key": f"experience_{i}",
                    "label": label,
                    "value": value,
                    "status": "ready",
                    "locked": False,
                    "group": "experience",
                    "company": company,
                    "title": title,
                    "dates": dates,
                }
            )
        return fields

    async def update_fields(
        self,
        user_id: UUID,
        application_id: UUID,
        updates: dict[str, str],
    ) -> dict[str, Any]:
        app = await self._load_app(user_id, application_id)
        state = copy.deepcopy(dict(app.workflow_state or {}))
        session = state.get("apply_session")
        if not session:
            raise HTTPException(status_code=404, detail="No apply session")
        fields = list(session.get("form_fields") or [])
        allowed = {f.get("key") for f in fields if not f.get("locked")}
        for key, value in (updates or {}).items():
            if key not in allowed:
                continue
            limit = 400 if str(key).startswith("experience_") else 200
            for f in fields:
                if f.get("key") == key:
                    f["value"] = str(value)[:limit]
                    f["status"] = "ready" if str(value).strip() else "manual"
        session["form_fields"] = fields
        session["updated_at"] = _utc_now().isoformat()
        self._save_session(app, session)
        await self.db.commit()
        await self.db.refresh(app)
        session = (app.workflow_state or {}).get("apply_session") or session
        return self._serialize(app, session)

    def _serialize(self, app: DBApplication, session: dict[str, Any]) -> dict[str, Any]:
        job = app.job
        state = app.workflow_state or {}
        return {
            "session_id": session["id"],
            "application_id": str(app.id),
            "job_id": str(app.job_id),
            "mode": "review_and_apply",
            "mode_note": (
                "Review & Apply: we prepare fields and a receipt; "
                "you approve each step and click Submit on the employer site."
            ),
            "status": session.get("status", "active"),
            "current_step_index": session.get("current_step_index", 0),
            "company": _company(job),
            "role_title": _display_role(job),
            "job_url": job.url if job else None,
            "steps": session.get("steps", []),
            "form_fields": session.get("form_fields", []),
            "receipt": session.get("receipt"),
            "package": session.get("package"),
            "docs": session.get("docs") or self._docs_payload(state, job),
            "browser": session.get("browser", {}),
            "updated_at": session.get("updated_at"),
            "experience": [
                f
                for f in (session.get("form_fields") or [])
                if f.get("group") == "experience"
            ],
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
        _, library_text = self._library_resume_text(app.job)
        form_fields = await self._profile_fields(user, app.job)
        docs = self._docs_payload(state, app.job, resume_text=library_text)

        if (
            not reset
            and isinstance(existing, dict)
            and existing.get("status")
            in ("active", "awaiting_submit_confirm", "completed")
            and existing.get("steps")
        ):
            if existing.get("status") != "completed":
                self._ensure_step_statuses(existing)
                old_by_key = {
                    f.get("key"): f for f in (existing.get("form_fields") or [])
                }
                merged = []
                for f in form_fields:
                    old = old_by_key.get(f.get("key"))
                    if (
                        old
                        and not f.get("locked")
                        and str(old.get("value") or "").strip()
                    ):
                        f = {
                            **f,
                            "value": old.get("value"),
                            "status": old.get("status") or f.get("status"),
                        }
                    merged.append(f)
                existing["form_fields"] = merged
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
        session = copy.deepcopy(session)
        _, library_text = self._library_resume_text(app.job)
        session["docs"] = self._docs_payload(
            app.workflow_state or {}, app.job, resume_text=library_text
        )
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
        now = _utc_now().isoformat()
        # Review-form Submit: auto-approve remaining HITL gates (user reviewed the mapped form)
        for s in steps:
            if s.get("status") != "approved":
                s["status"] = "approved"
                s["approved_at"] = now
        session["steps"] = steps
        session["current_step_index"] = max(len(steps) - 1, 0)
        session["status"] = "completed"
        session["completed_at"] = _utc_now().isoformat()
        fields = list(session.get("form_fields") or [])
        docs = session.get("docs") or {}
        pkg = docs.get("package") if isinstance(docs.get("package"), dict) else {}
        session["receipt"] = {
            "submitted_at": session["completed_at"],
            "company": _company(app.job),
            "role_title": _display_role(app.job),
            "job_url": app.job.url if app.job else None,
            "fields": [
                {"label": f.get("label"), "value": f.get("value"), "status": f.get("status")}
                for f in fields
            ],
            "field_count": len(fields),
            "filled_count": sum(
                1
                for f in fields
                if str(f.get("value") or "").strip()
                and f.get("status") in ("filled", "ready", "review")
            ),
            "resume": pkg.get("folder")
            or ("tailored" if docs.get("has_tailored_resume") else "library"),
            "ats_score": docs.get("ats_score"),
            "cover_letter": bool(docs.get("has_cover_letter")),
            "note": "You confirmed Submit on the employer site. Career OS did not silent-submit.",
        }
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
