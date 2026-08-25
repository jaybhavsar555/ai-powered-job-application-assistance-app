from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from sqlalchemy.orm import selectinload
from typing import Any, Optional

from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.infrastructure.db.models import DBApplication, DBJob, DBMessage, DBWikiEntity
from app.application.services.follow_up import list_follow_ups_due
from app.application.services.apply_prefs import ApplyPrefsService
from app.application.services.screening_qa import ENTITY_TYPE as SCREENING_QA_TYPE
from app.core.config import get_settings
from app.infrastructure.resume_library import list_resume_files
from app.application.services.mail import MailService

router = APIRouter()

# Stages still worth a fast apply push when the job/app is fresh
_FRESH_APPLY_STAGES = frozenset(
    {"Wishlist", "Researching", "Ready", "Needs input", "Reapply"}
)

_START_APPLY_STAGES = frozenset({"Wishlist", "Ready", "Reapply", "Researching"})


# Optim Hire–style apply loop (Review & Apply). Auto board-submit is NOT claimed.
PIPELINE_STEPS = [
    {
        "id": "discover",
        "title": "Discover / Import",
        "desc": "Find roles (Discovery or Vault portal → copy URL) with JD + link.",
        "href": "/discovery",
    },
    {
        "id": "wishlist",
        "title": "Wishlist",
        "desc": "Add matches you want — lands in Jobs / Tracker.",
        "href": "/jobs",
    },
    {
        "id": "tailor",
        "title": "Tailor (Canvas)",
        "desc": "AI reads JD → resume + cover letter from your data.",
        "href": "/canvas",
    },
    {
        "id": "approve",
        "title": "Approve",
        "desc": "Human review (Review & Apply mode) — nothing ships without you.",
        "href": "/approvals",
    },
    {
        "id": "package",
        "title": "Package",
        "desc": "Generate DOCX/PDF apply package on disk.",
        "href": "/jobs",
    },
    {
        "id": "apply",
        "title": "Review & Apply",
        "desc": "Guided session: open site, map form fields, human approve each gate, you click Submit.",
        "href": "/apply",
    },
    {
        "id": "follow_up",
        "title": "Follow-up (~3 days)",
        "desc": "Human-tone draft is queued; send from Outreach when due.",
        "href": "/outreach",
    },
]


def _company_name(job: Optional[DBJob]) -> str:
    if not job:
        return "Unknown"
    if job.company and job.company.name:
        return job.company.name
    normalized = job.description_normalized or {}
    return str(normalized.get("company_name") or "Unknown")


def _app_freshness(app: DBApplication) -> Optional[datetime]:
    """Prefer job posted/created time, else application created_at."""
    job = app.job
    if job and job.created_at:
        return job.created_at
    return app.created_at


def _list_new_jobs_48h(apps: list[DBApplication]) -> list[dict[str, Any]]:
    cutoff = datetime.utcnow() - timedelta(hours=48)
    out: list[dict[str, Any]] = []
    for app in apps:
        stage = app.stage or "Wishlist"
        if stage not in _FRESH_APPLY_STAGES:
            continue
        created = _app_freshness(app)
        if not created or created < cutoff:
            continue
        job = app.job
        company = _company_name(job)
        role = job.role_title if job else "Open role"
        job_id = str(job.id) if job else str(app.job_id)
        age_h = max(0, int((datetime.utcnow() - created).total_seconds() // 3600))
        out.append(
            {
                "application_id": str(app.id),
                "job_id": job_id,
                "company": company,
                "role_title": role,
                "stage": stage,
                "url": job.url if job else None,
                "age_hours": age_h,
                "ats_score": (app.workflow_state or {}).get("ats_score"),
                "label": f"New job < 48h — apply now · {company}",
                "href": f"/apply?job_id={job_id}",
                "created_at": created.isoformat() if created else None,
            }
        )
    out.sort(key=lambda x: x.get("age_hours") or 0)
    return out


def _pick_next_action(
    apps: list[DBApplication],
    follow_ups: list[dict[str, Any]],
    new_jobs_48h: Optional[list[dict[str, Any]]] = None,
) -> Optional[dict[str, Any]]:
    """Prefer due follow-ups, then fresh <48h roles, then Ready + high ATS."""
    if follow_ups:
        fu = follow_ups[0]
        return {
            "action": "follow_up",
            "label": f"Send follow-up — {fu.get('company')} ({fu.get('role_title') or 'role'})",
            "reason": "Applied ~3 days ago — review the human-tone draft and send from Outreach.",
            "href": "/outreach",
            "job_id": fu.get("job_id"),
            "application_id": fu.get("application_id"),
            "company": fu.get("company"),
            "role_title": fu.get("role_title"),
            "stage": "Applied",
            "ats_score": None,
            "estimated_minutes": 5,
        }

    if new_jobs_48h:
        nj = new_jobs_48h[0]
        return {
            "action": "apply_now",
            "label": nj["label"],
            "reason": (
                f"Posted/imported ~{nj.get('age_hours', 0)}h ago — apply within 48h "
                "for better odds (Review & Apply)."
            ),
            "href": nj["href"],
            "job_id": nj["job_id"],
            "application_id": nj["application_id"],
            "company": nj["company"],
            "role_title": nj.get("role_title"),
            "stage": nj.get("stage"),
            "ats_score": nj.get("ats_score"),
            "estimated_minutes": 10,
        }

    ranked: list[tuple[int, DBApplication]] = []
    for app in apps:
        state = app.workflow_state or {}
        ats = state.get("ats_score")
        try:
            ats_i = int(ats) if ats is not None else -1
        except (TypeError, ValueError):
            ats_i = -1
        stage = app.stage or "Wishlist"
        if stage == "Ready":
            ranked.append((1000 + ats_i, app))
        elif stage == "Reapply":
            ranked.append((900 + ats_i, app))
        elif stage == "Needs input":
            ranked.append((800 + ats_i, app))
        elif state.get("requires_human_approval") and stage not in (
            "Ready",
            "Applied",
            "Rejected",
            "Failed",
        ):
            ranked.append((500 + ats_i, app))
        elif stage == "Wishlist":
            ranked.append((100 + ats_i, app))
        elif stage == "Researching":
            ranked.append((200 + ats_i, app))

    if not ranked:
        return None

    ranked.sort(key=lambda x: x[0], reverse=True)
    _, app = ranked[0]
    job = app.job
    state = app.workflow_state or {}
    ats = state.get("ats_score")
    stage = app.stage or "Wishlist"
    company = _company_name(job)
    role = job.role_title if job else "Open role"
    job_id = str(job.id) if job else str(app.job_id)

    if stage in ("Ready", "Reapply"):
        action = "apply"
        label = f"Apply to {company} — {role}"
        href = f"/apply?job_id={job_id}"
        reason = (
            "Package ready — open Review & Apply, submit on the job site, mark Applied."
            if stage == "Ready"
            else "Marked Reapply — open Review & Apply and try again."
        )
    elif stage == "Needs input":
        action = "needs_input"
        label = f"Add missing answers for {company}"
        href = "/screening-qa"
        reason = "Apply blocked on missing screening answers — fill Q&A bank, then Reapply."
    elif state.get("requires_human_approval"):
        action = "approve"
        label = f"Approve documents for {company}"
        href = f"/approvals?job_id={job_id}"
        reason = "Resume/cover letter waiting on human approval (Review & Apply)."
    elif state.get("outreach_draft") or state.get("message_id"):
        action = "outreach"
        label = f"Review outreach draft for {company}"
        href = "/outreach"
        reason = "Cold email draft is ready — copy/send after review."
    else:
        action = "run_canvas"
        label = f"Run AI pipeline for {company} — {role}"
        href = f"/canvas?job_id={job_id}"
        reason = "On Wishlist — Simulate Canvas to tailor resume, cover, and outreach."

    return {
        "action": action,
        "label": label,
        "reason": reason,
        "href": href,
        "job_id": job_id,
        "application_id": str(app.id),
        "company": company,
        "role_title": role,
        "stage": stage,
        "ats_score": ats,
        "estimated_minutes": 8 if action == "apply" else 12,
    }


@router.get("/summary")
async def get_inbox_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Career Inbox metrics + Optim Hire–style pipeline + recommended next action."""
    apps_result = await db.execute(
        select(DBApplication)
        .where(DBApplication.user_id == current_user.id)
        .options(
            selectinload(DBApplication.job).selectinload(DBJob.company),
        )
    )
    apps = list(apps_result.scalars().all())

    total = len(apps)
    wishlist_count = sum(1 for a in apps if a.stage == "Wishlist")
    ready_count = sum(1 for a in apps if a.stage == "Ready")
    applied_count = sum(1 for a in apps if a.stage == "Applied")
    pending_approvals = sum(
        1
        for a in apps
        if (a.workflow_state or {}).get("requires_human_approval")
        and a.stage not in ("Ready", "Applied", "Rejected", "Offer")
    )

    draft_messages = await db.execute(
        select(func.count())
        .select_from(DBMessage)
        .join(DBApplication, DBMessage.application_id == DBApplication.id)
        .where(
            DBApplication.user_id == current_user.id,
            DBMessage.status == "Draft",
        )
    )
    outreach_drafts = int(draft_messages.scalar() or 0)

    follow_ups = await list_follow_ups_due(db, current_user.id)
    new_jobs_48h = _list_new_jobs_48h(apps)
    next_action = _pick_next_action(apps, follow_ups, new_jobs_48h)

    # Highlight which pipeline step is active for the recommended app
    active_step = "discover"
    if next_action:
        mapping = {
            "follow_up": "follow_up",
            "apply": "apply",
            "apply_now": "apply",
            "needs_input": "apply",
            "approve": "approve",
            "outreach": "follow_up",
            "run_canvas": "tailor",
        }
        active_step = mapping.get(next_action["action"], "wishlist")
    elif wishlist_count:
        active_step = "wishlist"

    needs_input_count = sum(1 for a in apps if a.stage == "Needs input")
    failed_count = sum(1 for a in apps if a.stage == "Failed")
    reapply_count = sum(1 for a in apps if a.stage == "Reapply")

    prefs = await ApplyPrefsService(db).get(current_user.id)
    apply_mode = prefs.get("apply_mode") or "review_and_apply"
    skip_queue = prefs.get("skip_queue") or []

    start_applying = []
    for app in apps:
        stage = app.stage or "Wishlist"
        if stage not in _START_APPLY_STAGES and stage != "Failed":
            continue
        # Failed goes via Reapply; include Reapply + Ready + fresh Wishlist
        if stage == "Failed":
            continue
        job = app.job
        job_id = str(job.id) if job else str(app.job_id)
        start_applying.append(
            {
                "application_id": str(app.id),
                "job_id": job_id,
                "company": _company_name(job),
                "role_title": job.role_title if job else None,
                "stage": stage,
                "url": job.url if job else None,
                "href": f"/apply?job_id={job_id}",
                "priority": 3
                if stage == "Ready"
                else 2
                if stage == "Reapply"
                else 1,
            }
        )
    start_applying.sort(key=lambda x: x["priority"], reverse=True)

    mode_note = (
        "Auto Apply ON: extension may click Submit on allowlisted ATS when confidence "
        "is high. Captcha/login/missing answers pause → Needs input / Failed → Reapply. "
        "LinkedIn stays blocked."
        if apply_mode == "auto_apply" and prefs.get("auto_consent")
        else (
            "Review & Apply: we tailor + package + draft mail; extension autofills; "
            "you click Submit. Enable Auto mode below only with explicit consent."
        )
    )

    # Daily-apply readiness (blockers that stop the boring loop)
    settings = get_settings()
    resume_dir = Path(settings.RESUME_SOURCE_DIR)
    resume_files = list_resume_files(resume_dir) if resume_dir.exists() else []
    pkg_dir = (settings.APPLICATION_PACKAGE_DIR or "").strip()
    pkg_ok = bool(pkg_dir) and (
        Path(pkg_dir).exists() or True
    )  # will be created on first package
    qa_count = int(
        (
            await db.execute(
                select(func.count())
                .select_from(DBWikiEntity)
                .where(
                    DBWikiEntity.user_id == current_user.id,
                    DBWikiEntity.entity_type == SCREENING_QA_TYPE,
                )
            )
        ).scalar()
        or 0
    )
    packaged = sum(
        1
        for a in apps
        if isinstance((a.workflow_state or {}).get("apply_package"), dict)
        and (a.workflow_state or {}).get("apply_package", {}).get("files")
    )
    missing_url = sum(
        1
        for a in apps
        if a.stage in _START_APPLY_STAGES and a.job and not (a.job.url or "").strip()
    )
    with_url = sum(
        1
        for a in apps
        if a.stage in _START_APPLY_STAGES and a.job and (a.job.url or "").strip()
    )
    smtp_ok = MailService().smtp_configured

    checks = [
        {
            "id": "resumes",
            "ok": len(resume_files) > 0,
            "label": f"Resume library ({len(resume_files)} file(s))",
            "fix": "Add PDF/DOCX templates under RESUME_SOURCE_DIR",
            "href": "/resumes",
        },
        {
            "id": "package_dir",
            "ok": bool(pkg_dir),
            "label": "Package output folder configured",
            "fix": "Set APPLICATION_PACKAGE_DIR (e.g. ./data/packages)",
            "href": "/approvals",
        },
        {
            "id": "screening_qa",
            "ok": qa_count > 0,
            "label": f"Screening Q&A bank ({qa_count})",
            "fix": "Seed common answers so the extension can autofill",
            "href": "/screening-qa",
        },
        {
            "id": "queue",
            "ok": len(start_applying) > 0 or ready_count > 0,
            "label": f"Apply queue ({len(start_applying)} start / {ready_count} ready)",
            "fix": "Run Discovery → Wishlist, or import a portal URL",
            "href": "/discovery",
        },
        {
            "id": "packages",
            "ok": packaged > 0 or ready_count == 0,
            "label": f"Tailored packages ({packaged})",
            "fix": "Canvas → Approvals → Package before apply/outreach",
            "href": "/canvas",
        },
        {
            "id": "job_urls",
            # Soft: OK if at least one applyable URL exists (or none queued)
            "ok": missing_url == 0 or with_url > 0,
            "label": (
                "Jobs have apply URLs"
                if missing_url == 0
                else f"{with_url} with URL · {missing_url} missing (fix on Jobs)"
            ),
            "fix": "Paste real ATS links on Jobs for roles without URLs"
            if missing_url
            else None,
            "href": "/jobs",
        },
        {
            "id": "outreach",
            "ok": True,
            "label": (
                "SMTP configured — can send from Outreach"
                if smtp_ok
                else "Outreach via mailto/copy (SMTP optional)"
            ),
            "fix": None,
            "href": "/outreach",
        },
    ]
    blockers = [c for c in checks if not c["ok"]]
    readiness = {
        "ready_for_daily_apply": len(blockers) == 0,
        "checks": checks,
        "blockers": blockers,
        "playbook": [
            "Inbox → pick Today's focus (or Start applying list)",
            "Canvas → Approvals → Package for that job",
            "Review & Apply + Chrome extension Fill (you click Submit)",
            "Outreach: edit draft, preview resume, send or mailto → Mark sent",
            "Confirm Submitted → follow-up draft queues automatically",
        ],
    }

    digest_lines: list[str] = []
    if new_jobs_48h:
        digest_lines.append(
            f"{len(new_jobs_48h)} new role(s) under 48h — apply now for better odds."
        )
    if ready_count:
        digest_lines.append(f"{ready_count} Ready to apply via Review & Apply.")
    if follow_ups:
        digest_lines.append(
            f"{len(follow_ups)} follow-up draft(s) due — send from Outreach."
        )
    if needs_input_count:
        digest_lines.append(
            f"{needs_input_count} paused on captcha/login/missing answers."
        )
    if failed_count or reapply_count:
        digest_lines.append(
            f"{failed_count} Failed / {reapply_count} Reapply — fix then resume."
        )
    if not digest_lines:
        digest_lines.append("Quiet day — run Discovery or import a portal URL.")

    return {
        "total_applications": total,
        "wishlist_count": wishlist_count,
        "ready_count": ready_count,
        "applied_count": applied_count,
        "needs_input_count": needs_input_count,
        "failed_count": failed_count,
        "reapply_count": reapply_count,
        "pending_approvals": pending_approvals,
        "outreach_drafts": outreach_drafts,
        "follow_ups_due": len(follow_ups),
        "follow_ups": follow_ups,
        "new_jobs_48h_count": len(new_jobs_48h),
        "new_jobs_48h": new_jobs_48h[:12],
        "start_applying_count": len(start_applying),
        "start_applying": start_applying[:15],
        "skip_queue": skip_queue[:10],
        "next_action": next_action,
        "apply_mode": apply_mode,
        "apply_mode_note": mode_note,
        "auto_consent": bool(prefs.get("auto_consent")),
        "work_authorization": prefs.get("work_authorization") or "",
        "auto_usage": prefs.get("usage"),
        "pipeline_steps": PIPELINE_STEPS,
        "pipeline_stages": [
            {
                "id": "find",
                "title": "Find",
                "desc": "Vault ATS/portals + boards. Match % before LinkedIn noise.",
                "href": "/discovery",
            },
            {
                "id": "prep",
                "title": "Prep",
                "desc": "Tailor resume + cover from facts. Diff on Approvals — nothing silent.",
                "href": "/tailor",
            },
            {
                "id": "apply",
                "title": "Apply",
                "desc": "Extension fills the ATS. You click Submit. Receipt saved.",
                "href": "/apply",
            },
            {
                "id": "track",
                "title": "Track",
                "desc": "Applied → follow-up ~3 days. Replies stay on the job, not a spreadsheet.",
                "href": "/tracker",
            },
        ],
        "active_pipeline_step": active_step,
        "readiness": readiness,
        "digest": {
            "headline": "Career OS daily digest",
            "summary_lines": digest_lines,
        },
        "positioning": {
            "headline": "Tailored resume + cover + outreach — then autofill the form",
            "quality_first": True,
            "modes": ["review_and_apply", "auto_apply"],
        },
    }


@router.get("/digest")
async def get_daily_digest(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """OptimHire-style daily digest snapshot (also used by Inbox alerts)."""
    apps_result = await db.execute(
        select(DBApplication)
        .where(DBApplication.user_id == current_user.id)
        .options(selectinload(DBApplication.job).selectinload(DBJob.company))
    )
    apps = list(apps_result.scalars().all())
    new_jobs_48h = _list_new_jobs_48h(apps)
    follow_ups = await list_follow_ups_due(db, current_user.id)
    prefs = await ApplyPrefsService(db).get(current_user.id)

    failed = [a for a in apps if a.stage == "Failed"]
    needs = [a for a in apps if a.stage == "Needs input"]
    reapply = [a for a in apps if a.stage == "Reapply"]
    ready = [a for a in apps if a.stage == "Ready"]

    def _brief(app: DBApplication) -> dict[str, Any]:
        job = app.job
        return {
            "application_id": str(app.id),
            "company": _company_name(job),
            "role_title": job.role_title if job else None,
            "stage": app.stage,
            "href": f"/apply?job_id={job.id}" if job else "/tracker",
        }

    lines = []
    if new_jobs_48h:
        lines.append(f"{len(new_jobs_48h)} new role(s) under 48h — apply now for better odds.")
    if ready:
        lines.append(f"{len(ready)} Ready to apply via Review & Apply / extension.")
    if follow_ups:
        lines.append(f"{len(follow_ups)} follow-up draft(s) due — send from Outreach.")
    if needs:
        lines.append(f"{len(needs)} paused on captcha/login/missing answers (Needs input).")
    if failed or reapply:
        lines.append(
            f"{len(failed)} Failed / {len(reapply)} Reapply — fix blockers then resume."
        )
    if not lines:
        lines.append("Quiet day — run Discovery or import a portal URL.")

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "headline": "Career OS daily digest",
        "apply_mode": prefs.get("apply_mode"),
        "summary_lines": lines,
        "new_jobs_48h": new_jobs_48h[:8],
        "ready": [_brief(a) for a in ready[:8]],
        "follow_ups_due": follow_ups[:8],
        "needs_input": [_brief(a) for a in needs[:8]],
        "failed": [_brief(a) for a in failed[:8]],
        "reapply": [_brief(a) for a in reapply[:8]],
        "skip_queue": (prefs.get("skip_queue") or [])[:8],
        "cta": {
            "start_applying": "/apply",
            "discovery": "/discovery",
            "screening_qa": "/screening-qa",
            "tracker": "/tracker",
        },
    }
