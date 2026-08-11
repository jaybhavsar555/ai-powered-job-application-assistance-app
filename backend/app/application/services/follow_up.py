"""Follow-up scheduling after Applied — Optim Hire–style reminder loop (human HITL send)."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import DBApplication, DBJob, DBMessage, DBRecruiter
from app.infrastructure.llm.client import structured_generate

logger = logging.getLogger(__name__)

FOLLOW_UP_DAYS = 3
FOLLOW_UP_OFFSETS = (3, 7)  # day-3 + day-7 cadence (HITL send from Outreach)


class FollowUpDraft(BaseModel):
    subject_line: str = Field(..., description="Email subject")
    body: str = Field(..., description="Email body")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _company_name(job: Optional[DBJob]) -> str:
    if not job:
        return "the company"
    if job.company and job.company.name:
        return job.company.name
    normalized = job.description_normalized or {}
    return str(normalized.get("company_name") or "the company")


def _candidate_first_name(user_email: Optional[str] = None) -> str:
    """Sign-off from resume library contact line, else email local-part — never hardcode."""
    try:
        from pathlib import Path

        from app.core.config import get_settings
        from app.infrastructure.resume_library import (
            detect_role_family,
            extract_text,
            parse_contact,
            pick_base_resume,
        )

        settings = get_settings()
        source = Path(settings.RESUME_SOURCE_DIR) if settings.RESUME_SOURCE_DIR else None
        if source and source.exists():
            base = pick_base_resume(source, detect_role_family("", ""))
            if base:
                name, _ = parse_contact(extract_text(base.path))
                if name and name.strip() and name.strip().lower() != "candidate":
                    return name.strip().split()[0]
    except Exception:
        pass
    local = (user_email or "").split("@")[0].replace(".", " ").replace("_", " ").strip()
    bits = [b for b in local.split() if b and b.lower() not in {"dev", "mail"}]
    if bits:
        return bits[0].capitalize()
    return "there"


def _fallback_follow_up(
    *,
    candidate_first: str,
    company: str,
    role: str,
    recruiter_name: Optional[str],
) -> FollowUpDraft:
    who = recruiter_name or "Hiring Team"
    first = who.split()[0] if who else "there"
    subject = f"Following up — {role} at {company}"
    body = (
        f"Hi {first},\n\n"
        f"I applied for the {role} role at {company} a few days ago and wanted to "
        f"follow up briefly. I'm still very interested and happy to share anything "
        f"else that would help — portfolio, availability for a short call, or "
        f"clarifying questions.\n\n"
        f"Thanks for your time,\n{candidate_first}"
    )
    return FollowUpDraft(subject_line=subject, body=body)


async def _draft_follow_up_copy(
    *,
    company: str,
    role: str,
    recruiter_name: Optional[str],
    jd_snippet: str,
    candidate_first: str,
) -> FollowUpDraft:
    """Human, readable follow-up — LLM when available, template otherwise."""
    first = candidate_first or "there"
    fallback = lambda: _fallback_follow_up(
        candidate_first=first,
        company=company,
        role=role,
        recruiter_name=recruiter_name,
    )
    prompt = (
        "Write a short follow-up email after a job application (sent ~3 days ago).\n\n"
        "Rules:\n"
        "- Sound like a real person: warm, concise, no buzzword soup\n"
        "- Under 120 words\n"
        "- No emojis, no 'I hope this email finds you well' clichés\n"
        "- Match professional-but-human tone for tech hiring\n"
        "- Mention the role and company once; one soft CTA\n"
        f"- Sign off with first name only: {first}\n\n"
        f"Company: {company}\n"
        f"Role: {role}\n"
        f"Recruiter/hiring contact: {recruiter_name or 'Hiring Team'}\n"
        f"JD snippet: {(jd_snippet or 'n/a')[:800]}"
    )
    return await structured_generate(
        FollowUpDraft,
        [
            {
                "role": "system",
                "content": (
                    "You write human follow-up emails for job seekers. "
                    "Output structured fields only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        fallback=fallback,
    )


async def schedule_follow_up_on_applied(
    db: AsyncSession,
    app: DBApplication,
    *,
    days: int = FOLLOW_UP_DAYS,
) -> dict[str, Any]:
    """
    When user marks Applied: schedule day-3 + day-7 follow-up drafts.
    Does NOT send email — user reviews in Outreach.
    """
    state = dict(app.workflow_state or {})
    if state.get("follow_up_message_id") or state.get("follow_ups"):
        return {
            "scheduled": False,
            "reason": "follow_up_already_scheduled",
            "follow_up_due_at": state.get("follow_up_due_at"),
            "follow_up_message_id": state.get("follow_up_message_id"),
            "follow_ups": state.get("follow_ups"),
        }

    now = _utc_now()
    offsets = tuple(FOLLOW_UP_OFFSETS)
    if days not in offsets:
        # Preserve explicit single-day override from callers
        offsets = (days,)

    result = await db.execute(
        select(DBApplication)
        .where(DBApplication.id == app.id)
        .options(
            selectinload(DBApplication.job).selectinload(DBJob.company),
        )
    )
    app = result.scalars().one()
    job = app.job

    company = _company_name(job)
    role = job.role_title if job else "the role"
    jd = (job.description_raw if job else "") or ""

    recruiter_name = None
    recruiter_id = None
    msg_result = await db.execute(
        select(DBMessage)
        .where(DBMessage.application_id == app.id, DBMessage.recruiter_id.isnot(None))
        .order_by(DBMessage.created_at.desc())
        .limit(1)
    )
    prior = msg_result.scalars().first()
    if prior and prior.recruiter_id:
        recruiter_id = prior.recruiter_id
        rec = await db.get(DBRecruiter, prior.recruiter_id)
        if rec:
            recruiter_name = rec.name

    candidate_first = _candidate_first_name()

    follow_ups: list[dict[str, Any]] = []
    first_message_id: Optional[str] = None
    first_due: Optional[str] = None

    for offset in offsets:
        try:
            draft = await _draft_follow_up_copy(
                company=company,
                role=role,
                recruiter_name=recruiter_name,
                jd_snippet=jd,
                candidate_first=candidate_first,
            )
            from_llm = True
        except RuntimeError as exc:
            print(f"[follow_up] LLM unavailable — labeled template used ({exc})")
            draft = _fallback_follow_up(
                candidate_first=candidate_first,
                company=company,
                role=role,
                recruiter_name=recruiter_name,
            )
            from_llm = False

        # Slightly different subject for day-7 so drafts are distinguishable
        subject = draft.subject_line
        if offset >= 7 and "follow" in subject.lower():
            subject = f"Checking in — {role} at {company}"

        content = f"Subject: {subject}\n\n{draft.body}"
        if not from_llm:
            content = (
                "[TEMPLATE — LLM unavailable; edit before sending]\n\n" + content
            )
        content = f"[Follow-up day {offset}]\n{content}"

        message = DBMessage(
            application_id=app.id,
            recruiter_id=recruiter_id,
            content=content,
            message_type="FollowUp",
            status="Draft",
        )
        db.add(message)
        await db.flush()

        due = now + timedelta(days=offset)
        entry = {
            "days": offset,
            "due_at": due.isoformat(),
            "message_id": str(message.id),
            "sent": False,
        }
        follow_ups.append(entry)
        if first_message_id is None:
            first_message_id = str(message.id)
            first_due = due.isoformat()

    state["applied_at"] = now.isoformat()
    state["follow_up_due_at"] = first_due
    state["follow_up_message_id"] = first_message_id
    state["follow_up_days"] = offsets[0] if offsets else days
    state["follow_ups"] = follow_ups
    app.workflow_state = state
    await db.commit()

    return {
        "scheduled": True,
        "follow_up_due_at": first_due,
        "follow_up_message_id": first_message_id,
        "follow_ups": follow_ups,
        "message_type": "FollowUp",
        "status": "Draft",
        "note": (
            "Day-3 and day-7 follow-up drafts ready — send from Outreach after each due date "
            "(no auto-send)."
        ),
    }


def follow_up_is_due(app: DBApplication, now: Optional[datetime] = None) -> bool:
    state = app.workflow_state or {}
    if app.stage != "Applied":
        return False
    now = now or _utc_now()

    follow_ups = state.get("follow_ups")
    if isinstance(follow_ups, list) and follow_ups:
        for entry in follow_ups:
            if not isinstance(entry, dict) or entry.get("sent"):
                continue
            due_raw = entry.get("due_at")
            if not due_raw:
                continue
            try:
                due = datetime.fromisoformat(str(due_raw).replace("Z", "+00:00"))
            except ValueError:
                continue
            if due.tzinfo is None:
                due = due.replace(tzinfo=timezone.utc)
            if now >= due:
                return True
        return False

    # Legacy single follow-up
    due_raw = state.get("follow_up_due_at")
    if not due_raw:
        return False
    if state.get("follow_up_sent"):
        return False
    try:
        due = datetime.fromisoformat(str(due_raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    return now >= due


async def list_follow_ups_due(
    db: AsyncSession, user_id: UUID
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(DBApplication)
        .where(
            DBApplication.user_id == user_id,
            DBApplication.stage == "Applied",
        )
        .options(selectinload(DBApplication.job).selectinload(DBJob.company))
    )
    apps = list(result.scalars().all())
    now = _utc_now()
    out: list[dict[str, Any]] = []
    for app in apps:
        if not follow_up_is_due(app, now):
            continue
        job = app.job
        state = app.workflow_state or {}
        follow_ups = state.get("follow_ups")
        due_at = state.get("follow_up_due_at")
        message_id = state.get("follow_up_message_id")
        label_days = state.get("follow_up_days") or FOLLOW_UP_DAYS
        if isinstance(follow_ups, list):
            for entry in follow_ups:
                if not isinstance(entry, dict) or entry.get("sent"):
                    continue
                due_raw = entry.get("due_at")
                if not due_raw:
                    continue
                try:
                    due = datetime.fromisoformat(str(due_raw).replace("Z", "+00:00"))
                except ValueError:
                    continue
                if due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)
                if now >= due:
                    due_at = due_raw
                    message_id = entry.get("message_id")
                    label_days = entry.get("days") or label_days
                    break
        out.append(
            {
                "application_id": str(app.id),
                "job_id": str(app.job_id),
                "company": _company_name(job),
                "role_title": job.role_title if job else None,
                "follow_up_due_at": due_at,
                "follow_up_message_id": message_id,
                "follow_up_days": label_days,
                "href": "/outreach",
            }
        )
    return out
