"""Profile + events for Career OS Chrome extension (Review fill / gated Auto submit)."""

from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.application.services.screening_qa import ScreeningQAService
from app.application.services.apply_prefs import ApplyPrefsService
from app.application.services.auto_apply_bot import AutoApplyBot
from app.infrastructure.db.models import DBApplication
from app.infrastructure.resume_library import (
    detect_role_family,
    extract_text,
    list_resume_files,
    parse_contact,
    pick_base_resume,
)
from app.infrastructure.llm.client import structured_generate
from app.core.config import get_settings

router = APIRouter()


class ExtensionEventIn(BaseModel):
    event_type: str = Field(
        ...,
        description="evaluate | filled | submit_attempt | submitted | skip | reapply",
    )
    host: str = ""
    url: Optional[str] = None
    application_id: Optional[str] = None
    confidence: float = 0.0
    reason: Optional[str] = None
    detail: Optional[str] = None


class MapFieldsRequest(BaseModel):
    labels: list[str] = Field(..., description="List of unmatched form labels from the page")


class FieldMapping(BaseModel):
    label: str
    answer: str


class MapFieldsResponse(BaseModel):
    mappings: list[FieldMapping]


def _latest_packaged_resume(apps: list[DBApplication]) -> tuple[Optional[Path], Optional[str], Optional[str]]:
    """Return (path, filename, application_id) for newest tailored resume package."""
    best: tuple[Optional[Path], Optional[str], Optional[str]] = (None, None, None)
    best_ts = None
    for app in apps:
        state = app.workflow_state or {}
        pkg = state.get("apply_package") if isinstance(state.get("apply_package"), dict) else {}
        files = pkg.get("files") or {}
        raw = files.get("resume_pdf") or files.get("resume_docx")
        if not raw:
            continue
        path = Path(str(raw))
        if not path.is_file():
            continue
        ts = app.updated_at or app.created_at
        if best_ts is None or (ts and ts > best_ts):
            best_ts = ts
            best = (path, path.name, str(app.id))
    return best


@router.get("/profile")
async def extension_autofill_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Profile + apply prefs for the extension.
    Auto submit only when apply_mode=auto_apply + consent + allowlist + rate limits.
    Includes resume file hint for ATS upload fields.
    """
    settings = get_settings()
    name, contact = "Candidate", current_user.email
    phone = ""
    location = ""
    linkedin = ""
    try:
        source = Path(settings.RESUME_SOURCE_DIR) if settings.RESUME_SOURCE_DIR else None
        if source and source.exists():
            base = pick_base_resume(source, detect_role_family("", ""))
            if base:
                text = extract_text(base.path)
                name, contact = parse_contact(text)
                parts = [
                    p.strip()
                    for p in contact.replace("|", ",").split(",")
                    if p.strip()
                ]
                for p in parts:
                    if "@" in p:
                        contact = p
                    elif any(c.isdigit() for c in p) and "linkedin.com" not in p and "github.com" not in p:
                        phone = p
                    elif "linkedin.com" in p.lower():
                        linkedin = p
                    elif "github.com" in p.lower() or "portfolio" in p.lower():
                        pass
                    else:
                        location = p
    except Exception:
        pass

    if not name or name.lower() == "candidate":
        local = (current_user.email or "").split("@")[0]
        bits = [b for b in local.replace(".", " ").replace("_", " ").split() if b]
        skip = {"dev", "mail"}
        bits = [b for b in bits if b.lower() not in skip]
        if bits:
            name = " ".join(b.capitalize() for b in bits[:4])

    qa = await ScreeningQAService(db).list(current_user.id)
    prefs = await ApplyPrefsService(db).get(current_user.id)
    mode = prefs.get("apply_mode") or "review_and_apply"
    autofill_mode = "auto_submit" if mode == "auto_apply" and prefs.get("auto_consent") else "autofill_only"

    apps = (
        await db.execute(
            select(DBApplication).where(DBApplication.user_id == current_user.id)
        )
    ).scalars().all()
    pkg_path, pkg_name, pkg_app_id = _latest_packaged_resume(list(apps))
    resume_meta = {
        "available": False,
        "source": None,
        "filename": None,
        "application_id": None,
        "download_path": "/extension/resume-file",
        "note": "Add PDF/DOCX under data/resumes or run Quick Apply / Package first.",
    }
    if pkg_path and pkg_name:
        resume_meta = {
            "available": True,
            "source": "package",
            "filename": pkg_name,
            "application_id": pkg_app_id,
            "download_path": "/extension/resume-file",
            "note": "Latest tailored package resume — extension can attach to file inputs.",
        }
    else:
        source = Path(settings.RESUME_SOURCE_DIR) if settings.RESUME_SOURCE_DIR else None
        if source and list_resume_files(source):
            base = pick_base_resume(source, detect_role_family("", ""))
            if base:
                resume_meta = {
                    "available": True,
                    "source": "library",
                    "filename": base.name,
                    "application_id": None,
                    "download_path": "/extension/resume-file",
                    "note": "Base resume from library (no tailored package yet).",
                }

    return {
        "mode": autofill_mode,
        "apply_mode": mode,
        "note": (
            "Auto Apply: may click Submit when confidence + allowlist + rate limits pass."
            if autofill_mode == "auto_submit"
            else "Review & Apply: extension fills fields + resume file when possible; you click Submit."
        ),
        "profile": {
            "full_name": name,
            "first_name": (name.split() or ["Candidate"])[0],
            "last_name": " ".join(name.split()[1:]) if len(name.split()) > 1 else "",
            "email": current_user.email if "@" in current_user.email else contact,
            "phone": phone,
            "linkedin": linkedin,
            "location": location,
            "work_authorization": prefs.get("work_authorization") or "",
        },
        "resume": resume_meta,
        "screening_qa": qa[:50],
        "auto_apply": {
            "enabled": bool(prefs.get("auto_enabled_globally")),
            "consent": bool(prefs.get("auto_consent")),
            "min_confidence": prefs.get("min_confidence"),
            "max_per_hour": prefs.get("max_per_hour"),
            "max_per_day": prefs.get("max_per_day"),
            "usage": prefs.get("usage"),
            "allowlist": prefs.get("allowlist"),
            "blocklist": prefs.get("blocklist"),
            "skip_queue_count": len(prefs.get("skip_queue") or []),
        },
        "supported_hosts": prefs.get("allowlist") or ["*"],
        "loop_engineer_queue": _extension_apply_queue_summary(current_user.id),
    }


def _extension_apply_queue_summary(user_id) -> dict:
    from app.application.services.extension_apply_queue import list_queue

    pending = list_queue(user_id)
    return {
        "pending_count": len(pending),
        "items": pending[:8],
    }


@router.get("/apply-queue")
async def extension_apply_queue(
    current_user: User = Depends(get_current_user),
):
    """
  Jobs confirmed via Loop Engineer — open URL in browser, extension autofill + attach resume.
  """
    from app.application.services.extension_apply_queue import list_queue

    return {"queue": list_queue(current_user.id)}


@router.post("/apply-queue/{application_id}/done")
async def extension_apply_queue_done(
    application_id: str,
    current_user: User = Depends(get_current_user),
):
    from app.application.services.extension_apply_queue import mark_done

    ok = mark_done(current_user.id, application_id)
    return {"marked_done": ok}


@router.get("/resume-file")
async def extension_resume_file(
    application_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream the best resume for extension ATS upload:
    tailored package for application_id (or latest package), else library base.
    """
    settings = get_settings()
    path: Optional[Path] = None
    filename = "resume.pdf"

    if application_id:
        app = (
            await db.execute(
                select(DBApplication).where(
                    DBApplication.id == application_id,
                    DBApplication.user_id == current_user.id,
                )
            )
        ).scalars().first()
        if app:
            state = app.workflow_state or {}
            pkg = state.get("apply_package") if isinstance(state.get("apply_package"), dict) else {}
            files = pkg.get("files") or {}
            raw = files.get("resume_pdf") or files.get("resume_docx")
            if raw and Path(str(raw)).is_file():
                path = Path(str(raw))
                filename = path.name

    if path is None:
        apps = (
            await db.execute(
                select(DBApplication).where(DBApplication.user_id == current_user.id)
            )
        ).scalars().all()
        path, filename, _ = _latest_packaged_resume(list(apps))

    if path is None:
        source = Path(settings.RESUME_SOURCE_DIR) if settings.RESUME_SOURCE_DIR else None
        if source:
            base = pick_base_resume(source, detect_role_family("", ""))
            if base:
                path = base.path
                filename = base.name

    if path is None or not path.is_file():
        raise HTTPException(
            status_code=404,
            detail="No resume file found — add PDF/DOCX to data/resumes or run Quick Apply/Package.",
        )

    media = (
        "application/pdf"
        if path.suffix.lower() == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        path,
        media_type=media,
        filename=filename,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/events")
async def extension_events(
    data: ExtensionEventIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Extension reports fill / submit / skip so Career OS can enforce gates + stages."""
    bot = AutoApplyBot(db)
    return await bot.handle_event(
        current_user.id,
        event_type=data.event_type,
        host=data.host,
        url=data.url,
        application_id=data.application_id,
        confidence=data.confidence,
        reason=data.reason,
        detail=data.detail,
    )


@router.post("/map-fields", response_model=MapFieldsResponse)
async def map_unmatched_fields(
    data: MapFieldsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fallback LLM mapping for fields the fast regex couldn't match."""
    if not data.labels:
        return MapFieldsResponse(mappings=[])

    # Fetch profile context
    qa_list = await ScreeningQAService(db).list(current_user.id)
    qa_bits = []
    for q in qa_list[:50]:
        if isinstance(q, dict):
            qq, aa = q.get("question") or "", q.get("answer") or ""
        else:
            qq, aa = getattr(q, "question", "") or "", getattr(q, "answer", "") or ""
        if qq:
            qa_bits.append(f"Q: {qq}\nA: {aa}")
    qa_text = "\n".join(qa_bits)
    
    # Minimal profile fields
    profile_text = f"Name: Candidate\nEmail: {current_user.email}\n"

    system_msg = (
        "You are an autofill assistant. Match the provided form field labels to the user's data.\n"
        "User Data:\n"
        f"{profile_text}\n"
        "Screening Q&A:\n"
        f"{qa_text}\n\n"
        "Rules:\n"
        "- If a label matches user data or Q&A, provide the exact 'answer' to fill.\n"
        "- If it does not match anything, leave 'answer' blank or omit it.\n"
        "- Keep it extremely concise."
    )

    user_msg = "Map these form labels:\n" + "\n".join(f"- {lbl}" for lbl in data.labels[:20])

    messages = [
        {"role": "system", "content": system_msg},
        {"role": "user", "content": user_msg},
    ]

    try:
        res = await structured_generate(
            response_model=MapFieldsResponse,
            messages=messages,
            fallback=lambda: MapFieldsResponse(mappings=[]),
            max_tokens=500,
        )
        return res
    except Exception as e:
        print(f"Map fields LLM error: {e}")
        return MapFieldsResponse(mappings=[])
