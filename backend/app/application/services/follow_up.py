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
) -> FollowUpDraft:
    """Human, readable follow-up — LLM when available, template otherwise."""
    fallback = lambda: _fallback_follow_up(
        candidate_first="Jay",
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
        "- Mention the role and company once; one soft CTA\n\n"
        f"Company: {company}\n"
        f"Role: {role}\n"
        f"Recruiter/hiring contact: {recruiter_name or 'Hiring Team'}\n"
        f"JD snippet: {(jd_snippet or 'n/a')[:800]}"
    )
    try:
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
    except Exception as exc:
        logger.info(f"Follow-up LLM draft fallback: {exc}")
        return fallback()


async def schedule_follow_up_on_applied(
    db: AsyncSession,
    app: DBApplication,
    *,
    days: int = FOLLOW_UP_DAYS,
) -> dict[str, Any]:
    """
    When user marks Applied: schedule follow-up due date and create a Draft FollowUp message.
    Does NOT send email — user reviews in Outreach (Optim Hire Review & Apply style).
    """
    state = dict(app.workflow_state or {})
    if state.get("follow_up_message_id"):
        return {
            "scheduled": False,
            "reason": "follow_up_already_scheduled",
            "follow_up_due_at": state.get("follow_up_due_at"),
            "follow_up_message_id": state.get("follow_up_message_id"),
        }

    now = _utc_now()
    due = now + timedelta(days=days)

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

    draft = await _draft_follow_up_copy(
        company=company,
        role=role,
        recruiter_name=recruiter_name,
        jd_snippet=jd,
    )
    content = f"Subject: {draft.subject_line}\n\n{draft.body}"

    message = DBMessage(
        application_id=app.id,
        recruiter_id=recruiter_id,
        content=content,
        message_type="FollowUp",
        status="Draft",
    )
    db.add(message)
    await db.flush()

    state["applied_at"] = now.isoformat()
    state["follow_up_due_at"] = due.isoformat()
    state["follow_up_message_id"] = str(message.id)
    state["follow_up_days"] = days
    app.workflow_state = state
    await db.commit()

    return {
        "scheduled": True,
        "follow_up_due_at": due.isoformat(),
        "follow_up_message_id": str(message.id),
        "message_type": "FollowUp",
        "status": "Draft",
        "note": "Follow-up draft ready — send from Outreach after the due date (no auto-send).",
    }


def follow_up_is_due(app: DBApplication, now: Optional[datetime] = None) -> bool:
    state = app.workflow_state or {}
    due_raw = state.get("follow_up_due_at")
    if not due_raw or app.stage != "Applied":
        return False
    if state.get("follow_up_sent"):
        return False
    try:
        due = datetime.fromisoformat(str(due_raw).replace("Z", "+00:00"))
    except ValueError:
        return False
    now = now or _utc_now()
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
        out.append(
            {
                "application_id": str(app.id),
                "job_id": str(app.job_id),
                "company": _company_name(job),
                "role_title": job.role_title if job else None,
                "follow_up_due_at": state.get("follow_up_due_at"),
                "follow_up_message_id": state.get("follow_up_message_id"),
                "href": "/outreach",
            }
        )
    return out
