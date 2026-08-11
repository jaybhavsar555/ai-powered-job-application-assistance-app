from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from pathlib import Path
import copy

from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.infrastructure.db.models import DBMessage, DBApplication, DBJob, DBCompany, DBRecruiter
from app.application.services.mail import MailService
from app.application.agents.outreach_draft_agent import (
    OutreachDraftAgent,
    build_outreach_from_context,
)
from app.application.services.workflow_persistence import persist_outreach_draft
from sqlalchemy.orm.attributes import flag_modified

router = APIRouter()

PACKAGE_KINDS = ("resume_pdf", "resume_docx", "cover_pdf", "cover_docx")


def _package_exists(app: Optional[DBApplication]) -> bool:
    if not app:
        return False
    state = app.workflow_state or {}
    pkg = state.get("apply_package") if isinstance(state.get("apply_package"), dict) else {}
    files = pkg.get("files") or {}
    return any(raw and Path(str(raw)).is_file() for raw in files.values())


def _package_host_hint(folder: Optional[str]) -> Optional[str]:
    """Map container path to host-friendly folder for copy/reveal."""
    if not folder:
        return None
    raw = str(folder).replace("\\", "/").rstrip("/")
    if "/data/packages/" in raw or raw.startswith("/data/packages"):
        name = raw.split("/")[-1]
        return f"data/packages/{name}"
    return str(folder)


def _resume_attachment_specs(app: Optional[DBApplication]) -> list[tuple[Path, str]]:
    """Prefer PDF resume, else DOCX — for SMTP attach."""
    if not app:
        return []
    state = app.workflow_state or {}
    pkg = state.get("apply_package") if isinstance(state.get("apply_package"), dict) else {}
    files = pkg.get("files") or {}
    for kind in ("resume_pdf", "resume_docx"):
        raw = files.get(kind)
        if not raw:
            continue
        path = Path(str(raw))
        if path.is_file():
            return [(path, path.name)]
    return []


async def _mark_follow_up_cleared(
    db: AsyncSession,
    app: Optional[DBApplication],
    *,
    message_id: Optional[UUID] = None,
) -> None:
    if not app:
        return
    state = copy.deepcopy(dict(app.workflow_state or {}))
    state["follow_up_sent_at"] = datetime.utcnow().isoformat()
    follow_ups = state.get("follow_ups")
    if isinstance(follow_ups, list) and follow_ups:
        mid = str(message_id) if message_id else None
        for entry in follow_ups:
            if not isinstance(entry, dict) or entry.get("sent"):
                continue
            if mid and str(entry.get("message_id")) == mid:
                entry["sent"] = True
                break
        else:
            # Fallback: mark first due unsent entry
            for entry in follow_ups:
                if isinstance(entry, dict) and not entry.get("sent"):
                    entry["sent"] = True
                    break
        state["follow_ups"] = follow_ups
        pending = next(
            (e for e in follow_ups if isinstance(e, dict) and not e.get("sent")),
            None,
        )
        if pending:
            state["follow_up_sent"] = False
            state["follow_up_due_at"] = pending.get("due_at")
            state["follow_up_message_id"] = pending.get("message_id")
            state["follow_up_days"] = pending.get("days")
        else:
            state["follow_up_sent"] = True
    else:
        state["follow_up_sent"] = True
    app.workflow_state = state
    flag_modified(app, "workflow_state")
    await db.flush()


class MessageAttachment(BaseModel):
    kind: str
    name: str
    exists: bool
    download_url: Optional[str] = None
    preview_url: Optional[str] = None


class MessageOut(BaseModel):
    id: UUID
    created_at: datetime
    content: str
    message_type: str
    status: str
    recruiter_id: Optional[UUID] = None
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    recruiter_linkedin: Optional[str] = None
    role_title: Optional[str] = None
    company_name: Optional[str] = None
    subject_line: Optional[str] = None
    body: Optional[str] = None
    has_tailored_resume: bool = False
    application_id: Optional[UUID] = None
    job_id: Optional[UUID] = None
    attachments: List[MessageAttachment] = []
    package_folder: Optional[str] = None
    package_folder_hint: Optional[str] = None
    package_hint: Optional[str] = None
    contact_ready: bool = False
    smtp_configured: bool = False


class MessageUpdate(BaseModel):
    subject_line: Optional[str] = Field(None, min_length=3)
    body: Optional[str] = Field(None, min_length=20)


class MessageContactUpdate(BaseModel):
    """Paste recruiter contact so cold email / LinkedIn note can land."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=320)
    linkedin_url: Optional[str] = Field(None, max_length=500)


def _parse_subject_body(content: str) -> tuple[str, str]:
    text = (content or "").strip()
    if text.lower().startswith("subject:"):
        lines = text.split("\n", 1)
        subject = lines[0].split(":", 1)[1].strip()
        body = lines[1].lstrip("\n") if len(lines) > 1 else ""
        return subject, body
    return "", text


def _attachments_from_state(app: Optional[DBApplication]) -> tuple[list[MessageAttachment], Optional[str], Optional[str]]:
    if not app:
        return [], None, None
    state = app.workflow_state or {}
    pkg = state.get("apply_package") if isinstance(state.get("apply_package"), dict) else {}
    files = pkg.get("files") or {}
    folder = pkg.get("folder")
    out: list[MessageAttachment] = []
    for kind in PACKAGE_KINDS:
        raw = files.get(kind)
        exists = bool(raw and Path(str(raw)).is_file())
        name = Path(str(raw)).name if raw else kind
        out.append(
            MessageAttachment(
                kind=kind,
                name=name,
                exists=exists,
                download_url=(
                    f"/api/v1/documents/package-download?application_id={app.id}&kind={kind}"
                    if exists
                    else None
                ),
                preview_url=(
                    f"/api/v1/documents/package-preview?application_id={app.id}&kind={kind}"
                    if exists
                    else None
                ),
            )
        )
    if any(a.exists for a in out):
        hint = "Verify the tailored package resume before you send — preview PDF/DOCX below."
    elif state.get("tailored_resume"):
        hint = "Resume was tailored in Canvas but not packaged yet — run Package on Jobs/Tracker, then refresh."
    else:
        hint = "No package yet. Run Canvas → Approvals → Package so you can attach a JD-matched resume."
    return out, str(folder) if folder else None, hint


def _to_out(m: DBMessage) -> MessageOut:
    job = m.application.job if m.application else None
    company = job.company if job else None
    recruiter = m.recruiter
    subject, body = _parse_subject_body(m.content or "")
    attachments, folder, hint = _attachments_from_state(m.application)
    state = (m.application.workflow_state or {}) if m.application else {}
    company_name = None
    if company and company.name:
        company_name = company.name
    elif job and job.description_normalized:
        company_name = job.description_normalized.get("company_name")
    email = (recruiter.email if recruiter else None) or None
    linkedin = (recruiter.linkedin_url if recruiter else None) or None
    return MessageOut(
        id=m.id,
        created_at=m.created_at,
        content=m.content,
        message_type=m.message_type,
        status=m.status,
        recruiter_id=recruiter.id if recruiter else None,
        recruiter_name=recruiter.name if recruiter else None,
        recruiter_email=email,
        recruiter_linkedin=linkedin,
        role_title=job.role_title if job else None,
        company_name=company_name,
        subject_line=subject or None,
        body=body or (None if subject else m.content),
        has_tailored_resume=bool(
            state.get("tailored_resume") or state.get("apply_package")
        ),
        application_id=m.application_id,
        job_id=job.id if job else None,
        attachments=attachments,
        package_folder=folder,
        package_folder_hint=_package_host_hint(folder),
        package_hint=hint,
        contact_ready=bool((email or "").strip() or (linkedin or "").strip()),
        smtp_configured=MailService().smtp_configured,
    )


async def _load_user_message(
    db: AsyncSession, message_id: UUID, user_id: UUID
) -> DBMessage:
    stmt = (
        select(DBMessage)
        .join(DBApplication, DBMessage.application_id == DBApplication.id)
        .join(DBJob, DBApplication.job_id == DBJob.id)
        .where(DBMessage.id == message_id, DBJob.user_id == user_id)
        .options(
            joinedload(DBMessage.application)
            .joinedload(DBApplication.job)
            .joinedload(DBJob.company),
            joinedload(DBMessage.recruiter),
        )
    )
    result = await db.execute(stmt)
    db_message = result.scalars().first()
    if not db_message:
        raise HTTPException(status_code=404, detail="Message not found")
    return db_message


@router.get("", response_model=List[MessageOut])
@router.get("/", response_model=List[MessageOut], include_in_schema=False)
async def list_messages(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List messages for the current user's applications."""
    stmt = (
        select(DBMessage)
        .join(DBApplication, DBMessage.application_id == DBApplication.id)
        .join(DBJob, DBApplication.job_id == DBJob.id)
        .outerjoin(DBCompany, DBJob.company_id == DBCompany.id)
        .outerjoin(DBRecruiter, DBMessage.recruiter_id == DBRecruiter.id)
        .where(DBJob.user_id == current_user.id)
        .options(
            joinedload(DBMessage.application)
            .joinedload(DBApplication.job)
            .joinedload(DBJob.company),
            joinedload(DBMessage.recruiter),
        )
        .order_by(DBMessage.created_at.desc())
    )
    result = await db.execute(stmt)
    return [_to_out(m) for m in result.scalars().all()]


@router.patch("/{message_id}", response_model=MessageOut)
async def update_message_draft(
    message_id: UUID,
    data: MessageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit subject/body before send — you own the final wording."""
    db_message = await _load_user_message(db, message_id, current_user.id)
    if db_message.status == "Sent":
        raise HTTPException(status_code=400, detail="Cannot edit a sent message")
    subject, body = _parse_subject_body(db_message.content or "")
    if data.subject_line is not None:
        subject = data.subject_line.strip()
    if data.body is not None:
        body = data.body.strip()
    if not subject or not body:
        raise HTTPException(status_code=400, detail="Subject and body are required")
    db_message.content = f"Subject: {subject}\n\n{body}"
    await db.commit()
    await db.refresh(db_message)
    refreshed = await _load_user_message(db, db_message.id, current_user.id)
    return _to_out(refreshed)


@router.patch("/{message_id}/contact", response_model=MessageOut)
async def update_message_contact(
    message_id: UUID,
    data: MessageContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Paste recruiter name / email / LinkedIn on a draft.
    Empty To: emails get zero interviews — this is the manual gate.
    """
    db_message = await _load_user_message(db, message_id, current_user.id)
    if db_message.status == "Sent":
        raise HTTPException(status_code=400, detail="Cannot edit contact on a sent message")

    email = (data.email or "").strip() or None
    linkedin = (data.linkedin_url or "").strip() or None
    name = (data.name or "").strip() or None

    if email and "@" not in email:
        raise HTTPException(status_code=400, detail="Email looks invalid")
    if linkedin and "linkedin.com" not in linkedin.lower() and not linkedin.startswith("http"):
        linkedin = f"https://www.linkedin.com/in/{linkedin.lstrip('/')}"

    if not email and not linkedin and not name:
        raise HTTPException(
            status_code=400,
            detail="Provide at least an email, LinkedIn URL, or name",
        )

    app = db_message.application
    job = app.job if app else None
    company = job.company if job else None
    if company is None and job is not None:
        # Ensure a company row so recruiter FK works
        company_name = (
            (job.description_normalized or {}).get("company_name")
            if job.description_normalized
            else None
        ) or "Unknown Company"
        company = DBCompany(name=str(company_name), research_data={})
        db.add(company)
        await db.flush()
        job.company_id = company.id

    if company is None:
        raise HTTPException(
            status_code=400,
            detail="Message has no company — re-run Canvas or import the job again",
        )

    recruiter = db_message.recruiter
    if recruiter is None:
        recruiter = DBRecruiter(
            company_id=company.id,
            name=name or "Hiring Team",
            email=email,
            linkedin_url=linkedin,
        )
        db.add(recruiter)
        await db.flush()
        db_message.recruiter_id = recruiter.id
    else:
        if name:
            recruiter.name = name
        if data.email is not None:
            recruiter.email = email
        if data.linkedin_url is not None:
            recruiter.linkedin_url = linkedin

    if app:
        state = copy.deepcopy(dict(app.workflow_state or {}))
        state["recruiter_id"] = str(recruiter.id)
        app.workflow_state = state
        flag_modified(app, "workflow_state")

    await db.commit()
    refreshed = await _load_user_message(db, db_message.id, current_user.id)
    return _to_out(refreshed)


@router.post("/{message_id}/regenerate", response_model=MessageOut)
async def regenerate_message(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rebuild cold-email draft from company research + JD match + tailored resume.
    Uses LLM when available; otherwise a rich grounded template.
    """
    db_message = await _load_user_message(db, message_id, current_user.id)
    if db_message.status == "Sent":
        raise HTTPException(status_code=400, detail="Cannot regenerate a sent message")
    if db_message.message_type not in ("Email", "FollowUp"):
        raise HTTPException(status_code=400, detail="Only email drafts can be regenerated")

    app = db_message.application
    job = app.job if app else None
    if not app or not job:
        raise HTTPException(status_code=400, detail="Message has no linked job")

    state = dict(app.workflow_state or {})
    company_name = (
        job.company.name
        if job.company and job.company.name
        else (job.description_normalized or {}).get("company_name")
        or "the company"
    )
    agent_state = {
        "job_details": {
            **(job.description_normalized or {}),
            "role_title": job.role_title,
            "company_name": company_name,
            "description_raw": (job.description_raw or "")[:4000],
            "required_skills": (job.description_normalized or {}).get("required_skills")
            or [],
        },
        "company_research": state.get("company_research") or {"company_name": company_name},
        "tailored_resume": state.get("tailored_resume") or {},
        "matching_skills": state.get("matching_skills") or [],
        "apply_package": state.get("apply_package") or {},
        "recruiter_discovery": {
            "name": db_message.recruiter.name if db_message.recruiter else None,
            "recruiter_name": db_message.recruiter.name if db_message.recruiter else None,
            "recruiter_email": db_message.recruiter.email if db_message.recruiter else None,
        },
        "company": company_name,
        "candidate_name": None,
    }

    try:
        agent = OutreachDraftAgent()
        result = await agent.run(agent_state)
        draft = result.get("outreach_draft") or build_outreach_from_context(
            agent_state
        ).model_dump()
    except Exception:
        draft = build_outreach_from_context(agent_state).model_dump()

    message = await persist_outreach_draft(
        db,
        job_id=str(job.id),
        draft=draft,
        recruiter_id=str(db_message.recruiter_id) if db_message.recruiter_id else None,
    )
    if not message:
        raise HTTPException(status_code=500, detail="Failed to save regenerated draft")

    refreshed = await _load_user_message(db, message.id, current_user.id)
    return _to_out(refreshed)


@router.post("/{message_id}/send")
async def send_message(
    message_id: UUID,
    force: bool = Query(False, description="Send even if tailored package is missing"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-sends the drafted email via MailService and marks it as Sent."""
    db_message = await _load_user_message(db, message_id, current_user.id)

    if db_message.status == "Sent":
        raise HTTPException(status_code=400, detail="Message already sent")

    recruiter = db_message.recruiter
    to_email = (recruiter.email if recruiter else None) or None
    linkedin = (recruiter.linkedin_url if recruiter else None) or None

    if not to_email and not linkedin:
        raise HTTPException(
            status_code=400,
            detail=(
                "Add a recruiter email or LinkedIn URL on this draft before send. "
                "Empty To: gets zero interviews."
            ),
        )

    if not to_email and linkedin:
        return {
            "success": False,
            "contact_linkedin_only": True,
            "linkedin_url": linkedin,
            "message": (
                "No email on file — open LinkedIn to send a note, then click Mark sent. "
                "Paste an email if you want mailto/SMTP instead."
            ),
        }

    app = db_message.application
    if app and not _package_exists(app) and not force:
        return {
            "success": False,
            "package_required": True,
            "application_id": str(app.id),
            "job_id": str(app.job_id) if app.job_id else None,
            "message": (
                "No tailored package on this application. "
                "Generate Package from Approvals/Jobs first, or retry with force=true."
            ),
            "cta": f"/approvals?job_id={app.job_id}" if app.job_id else "/approvals",
        }

    job = app.job if app else None
    company = job.company if job else None
    company_name = (
        company.name
        if company
        else (
            job.description_normalized.get("company_name")
            if job and job.description_normalized
            else "Unknown"
        )
    )
    role = job.role_title if job else "Open Role"
    parsed_subject, parsed_body = _parse_subject_body(db_message.content or "")
    subject = parsed_subject or f"{role} at {company_name}"
    body = parsed_body or db_message.content or ""

    mail_service = MailService()
    attach_specs = _resume_attachment_specs(app)
    attachments, folder, _hint = _attachments_from_state(app)
    resume_att = next((a for a in attachments if a.kind == "resume_pdf" and a.exists), None)
    if resume_att is None:
        resume_att = next((a for a in attachments if a.kind == "resume_docx" and a.exists), None)

    if not mail_service.smtp_configured:
        from urllib.parse import quote

        mailto = (
            f"mailto:{quote(to_email)}?subject={quote(subject)}"
            f"&body={quote(body)}"
        )
        gmail = (
            "https://mail.google.com/mail/?view=cm&fs=1"
            f"&to={quote(to_email)}"
            f"&su={quote(subject)}"
            f"&body={quote(body)}"
        )
        return {
            "success": False,
            "smtp_configured": False,
            "mailto": mailto,
            "gmail_url": gmail,
            "package_folder": folder,
            "package_folder_hint": _package_host_hint(folder),
            "resume_download_url": resume_att.download_url if resume_att else None,
            "resume_filename": resume_att.name if resume_att else None,
            "message": (
                "SMTP not set — use Download PDF & open Gmail (paperclip the file), "
                "or copy the package folder path. Configure SMTP_* for true send-with-attach. "
                "Click Mark sent after you send."
            ),
        }

    try:
        mail_service.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            attachments=attach_specs,
        )
        db_message.status = "Sent"
        if (db_message.message_type or "").lower().replace("_", "") == "followup":
            await _mark_follow_up_cleared(db, app, message_id=db_message.id)
        await db.commit()
        return {
            "success": True,
            "smtp_configured": True,
            "attached": [name for _, name in attach_specs],
            "message": (
                f"Email sent with {len(attach_specs)} attachment(s)."
                if attach_specs
                else "Email sent (no package file found to attach — package first next time)."
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")


@router.post("/{message_id}/mark-sent")
async def mark_message_sent(
    message_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark draft as Sent after mailto/manual send — clears follow-up due loop."""
    db_message = await _load_user_message(db, message_id, current_user.id)
    if db_message.status == "Sent":
        return {"success": True, "status": "Sent", "already": True}
    db_message.status = "Sent"
    if (db_message.message_type or "").lower().replace("_", "") == "followup":
        await _mark_follow_up_cleared(db, db_message.application, message_id=db_message.id)
    await db.commit()
    return {"success": True, "status": "Sent"}
