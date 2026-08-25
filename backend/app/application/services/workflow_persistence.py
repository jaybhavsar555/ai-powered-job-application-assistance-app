"""Persist LangGraph workflow outputs into Postgres so Simple Mode pages stay in sync."""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import (
    DBApplication,
    DBCompany,
    DBJob,
    DBMessage,
    DBRecruiter,
)


async def _get_job_and_app(
    db: AsyncSession, job_id: Optional[str]
) -> tuple[Optional[DBJob], Optional[DBApplication]]:
    if not job_id:
        return None, None
    try:
        uid = UUID(str(job_id))
    except (ValueError, TypeError):
        return None, None

    job = (
        await db.execute(
            select(DBJob)
            .where(DBJob.id == uid)
            .options(selectinload(DBJob.application), selectinload(DBJob.company))
        )
    ).scalars().first()
    if not job:
        return None, None

    app = job.application
    if app is None:
        app = (
            await db.execute(
                select(DBApplication).where(
                    DBApplication.job_id == job.id,
                    DBApplication.user_id == job.user_id,
                )
            )
        ).scalars().first()
    return job, app


def _patch_workflow_state(app: Optional[DBApplication], patch: dict[str, Any]) -> None:
    if app is None:
        return
    state = dict(app.workflow_state or {})
    state.update(patch)
    app.workflow_state = state


async def persist_company_research(
    db: AsyncSession,
    *,
    job_id: Optional[str],
    research: dict[str, Any],
) -> Optional[DBCompany]:
    job, app = await _get_job_and_app(db, job_id)
    if not job:
        return None

    name = (
        (research or {}).get("company_name")
        or (job.description_normalized or {}).get("company_name")
        or "Unknown Company"
    )
    name = str(name).strip() or "Unknown Company"

    existing = (
        await db.execute(
            select(DBCompany).where(func.lower(DBCompany.name) == name.lower())
        )
    ).scalars().first()

    if existing:
        data = dict(existing.research_data or {})
        data.update(research or {})
        existing.research_data = data
        company = existing
    else:
        company = DBCompany(name=name, research_data=dict(research or {}))
        db.add(company)
        await db.flush()

    job.company_id = company.id
    normalized = dict(job.description_normalized or {})
    normalized["company_name"] = company.name
    if research:
        normalized["company_research"] = research
    job.description_normalized = normalized

    _patch_workflow_state(
        app,
        {
            "company_research": research,
            "company_id": str(company.id),
        },
    )
    await db.commit()
    await db.refresh(company)
    return company


async def persist_recruiter_discovery(
    db: AsyncSession,
    *,
    job_id: Optional[str],
    discovery: dict[str, Any],
) -> Optional[DBRecruiter]:
    job, app = await _get_job_and_app(db, job_id)
    if not job:
        return None

    company = None
    if job.company_id:
        company = (
            await db.execute(select(DBCompany).where(DBCompany.id == job.company_id))
        ).scalars().first()

    if company is None:
        company_name = (
            (job.description_normalized or {}).get("company_name")
            or (discovery or {}).get("company_name")
            or "Unknown Company"
        )
        company = await persist_company_research(
            db,
            job_id=job_id,
            research={"company_name": company_name},
        )
        # re-load after nested commit
        job, app = await _get_job_and_app(db, job_id)
        if not job or not company:
            return None

    name = str((discovery or {}).get("recruiter_name") or "Hiring Team").strip()
    email = (discovery or {}).get("recruiter_email")
    if email is not None:
        email = str(email).strip() or None
    linkedin = (discovery or {}).get("linkedin_url")
    if linkedin is not None:
        linkedin = str(linkedin).strip() or None

    recruiter = None
    if email:
        recruiter = (
            await db.execute(
                select(DBRecruiter).where(
                    DBRecruiter.company_id == company.id,
                    func.lower(DBRecruiter.email) == email.lower(),
                )
            )
        ).scalars().first()
    if recruiter is None:
        recruiter = (
            await db.execute(
                select(DBRecruiter).where(
                    DBRecruiter.company_id == company.id,
                    func.lower(DBRecruiter.name) == name.lower(),
                )
            )
        ).scalars().first()

    if recruiter:
        recruiter.name = name
        if email:
            recruiter.email = email
        if linkedin:
            recruiter.linkedin_url = linkedin
    else:
        recruiter = DBRecruiter(
            company_id=company.id,
            name=name,
            email=email,
            linkedin_url=linkedin,
        )
        db.add(recruiter)
        await db.flush()

    _patch_workflow_state(
        app,
        {
            "recruiter_discovery": discovery,
            "recruiter_id": str(recruiter.id),
        },
    )
    await db.commit()
    await db.refresh(recruiter)
    return recruiter


async def persist_outreach_draft(
    db: AsyncSession,
    *,
    job_id: Optional[str],
    draft: dict[str, Any],
    recruiter_id: Optional[str] = None,
) -> Optional[DBMessage]:
    job, app = await _get_job_and_app(db, job_id)
    if not job or not app:
        return None

    body = str((draft or {}).get("body") or "").strip()
    subject = str((draft or {}).get("subject_line") or "").strip()
    if not body:
        return None

    content = body if not subject else f"Subject: {subject}\n\n{body}"

    rid: Optional[UUID] = None
    if recruiter_id:
        try:
            rid = UUID(str(recruiter_id))
        except (ValueError, TypeError):
            rid = None
    if rid is None:
        state_rid = (app.workflow_state or {}).get("recruiter_id")
        if state_rid:
            try:
                rid = UUID(str(state_rid))
            except (ValueError, TypeError):
                rid = None

    existing = (
        await db.execute(
            select(DBMessage).where(
                DBMessage.application_id == app.id,
                DBMessage.status == "Draft",
                DBMessage.message_type == "Email",
            )
        )
    ).scalars().first()

    if existing:
        existing.content = content
        if rid:
            existing.recruiter_id = rid
        message = existing
    else:
        message = DBMessage(
            application_id=app.id,
            recruiter_id=rid,
            content=content,
            message_type="Email",
            status="Draft",
        )
        db.add(message)
        await db.flush()

    _patch_workflow_state(
        app,
        {
            "outreach_draft": draft,
            "message_id": str(message.id),
        },
    )
    await db.commit()
    await db.refresh(message)
    return message


async def persist_ats_and_approval_flags(
    db: AsyncSession,
    *,
    job_id: Optional[str],
    ats_score: Optional[int] = None,
    missing_skills: Optional[list] = None,
    matching_skills: Optional[list] = None,
    ats_recommendation: Optional[str] = None,
    tailored_resume: Optional[dict] = None,
    cover_letter: Optional[str] = None,
    requires_human_approval: bool = False,
    ats_parser: Optional[dict] = None,
    ats_rationale: Optional[str] = None,
    qualifications_match: Optional[str] = None,
) -> None:
    job, app = await _get_job_and_app(db, job_id)
    if not app:
        return

    patch: dict[str, Any] = {}
    if ats_score is not None:
        patch["ats_score"] = ats_score
    if missing_skills is not None:
        patch["missing_skills"] = missing_skills
    if matching_skills is not None:
        patch["matching_skills"] = matching_skills
    if ats_recommendation is not None:
        patch["ats_recommendation"] = ats_recommendation
    if ats_parser is not None:
        patch["ats_parser"] = ats_parser
    if ats_rationale is not None:
        patch["ats_rationale"] = ats_rationale
    if qualifications_match is not None:
        patch["qualifications_match"] = qualifications_match
    if tailored_resume is not None:
        patch["tailored_resume"] = tailored_resume
    if cover_letter is not None:
        patch["cover_letter"] = cover_letter
    if requires_human_approval:
        patch["requires_human_approval"] = True
        if app.stage in ("Wishlist", "Researching"):
            app.stage = "Researching"

    _patch_workflow_state(app, patch)
    await db.commit()
