"""Profile + events for Career OS Chrome extension (Review fill / gated Auto submit)."""

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.application.services.screening_qa import ScreeningQAService
from app.application.services.apply_prefs import ApplyPrefsService
from app.application.services.auto_apply_bot import AutoApplyBot
from app.infrastructure.resume_library import (
    detect_role_family,
    extract_text,
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



@router.get("/profile")
async def extension_autofill_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Profile + apply prefs for the extension.
    Auto submit only when apply_mode=auto_apply + consent + allowlist + rate limits.
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
                    elif any(c.isdigit() for c in p) and not "linkedin.com" in p and not "github.com" in p:
                        phone = p
                    elif "linkedin.com" in p.lower():
                        linkedin = p
                    elif "github.com" in p.lower() or "portfolio" in p.lower():
                        pass # Ignore github/portfolio for now
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

    return {
        "mode": autofill_mode,
        "apply_mode": mode,
        "note": (
            "Auto Apply: may click Submit when confidence + allowlist + rate limits pass."
            if autofill_mode == "auto_submit"
            else "Review & Apply: extension fills fields; you click Submit."
        ),
        "profile": {
            "full_name": name,
            "first_name": (name.split() or ["Candidate"])[0],
            "last_name": " ".join(name.split()[1:]) if len(name.split()) > 1 else "",
            "email": current_user.email if "@" in current_user.email else contact,
            "phone": phone,
            "linkedin": linkedin,
            "location": location,
            "work_authorization": "",
        },
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
    }


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
    qa_text = "\n".join([f"Q: {q.question}\nA: {q.answer}" for q in qa_list[:50]])
    
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
