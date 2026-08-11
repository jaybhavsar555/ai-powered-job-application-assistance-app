"""One-shot: paste LinkedIn hiring post → job + tailored package + outreach draft."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.application.services.apply_package import ApplyPackageService
from app.application.services.hiring_post import (
    ParsedHiringPost,
    build_interest_email,
    parse_hiring_post,
)
from app.application.services.job_urls import clean_role_title, normalize_job_url
from app.application.services.workflow_persistence import (
    persist_outreach_draft,
    persist_recruiter_discovery,
)
from app.core.config import get_settings
from app.infrastructure.db.models import DBApplication, DBJob
from app.infrastructure.resume_library import list_resume_files


class QuickApplyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _create_job_fast(
        self,
        user_id: UUID,
        parsed: ParsedHiringPost,
        source_url: Optional[str],
    ) -> DBJob:
        """Create wishlist job from parsed post — no LLM intake (avoids proxy timeouts)."""
        url = normalize_job_url(parsed.linkedin_post_url or source_url)
        if url:
            existing = (
                await self.db.execute(
                    select(DBJob).where(DBJob.user_id == user_id, DBJob.url == url)
                )
            ).scalars().first()
            if existing:
                return existing

        role_title = clean_role_title(parsed.role_title, default="Open Role")
        company = (parsed.company_name or "LinkedIn hiring post").strip()
        normalized = {
            "role_title": role_title,
            "company_name": company,
            "required_skills": parsed.required_skills or [],
            "nice_to_have_skills": [],
            "years_of_experience": None,
            "responsibilities": [],
            "benefits": [],
            "location": parsed.location,
            "_source": "hiring_post_paste",
        }

        job = DBJob(
            user_id=user_id,
            url=url,
            role_title=role_title,
            description_raw=parsed.description,
            description_normalized=normalized,
            status="Wishlist",
        )
        self.db.add(job)
        await self.db.flush()

        app = DBApplication(
            user_id=user_id,
            job_id=job.id,
            stage="Wishlist",
            workflow_state={},
        )
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def from_hiring_post(
        self,
        user_id: UUID,
        *,
        post_text: str,
        source_url: Optional[str] = None,
        contact_email_override: Optional[str] = None,
        contact_name_override: Optional[str] = None,
        run_package: bool = True,
        candidate_name: Optional[str] = None,
    ) -> dict[str, Any]:
        try:
            parsed = parse_hiring_post(post_text, source_url=source_url)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        email = (contact_email_override or parsed.contact_email or "").strip() or None
        name = (contact_name_override or parsed.contact_name or "").strip() or None
        if email:
            parsed.contact_email = email
        if name:
            parsed.contact_name = name

        settings = get_settings()
        resume_dir = Path(settings.RESUME_SOURCE_DIR)
        library = list_resume_files(resume_dir)

        job = await self._create_job_fast(user_id, parsed, source_url)

        app_result = await self.db.execute(
            select(DBApplication).where(
                DBApplication.job_id == job.id,
                DBApplication.user_id == user_id,
            )
        )
        app = app_result.scalars().first()
        if not app:
            raise HTTPException(
                status_code=500, detail="Wishlist application missing after ingest"
            )

        discovery = {
            "recruiter_name": name or "Hiring Team",
            "recruiter_email": email or "",
            "linkedin_url": parsed.linkedin_profile_url,
            "confidence": 0.9 if email else 0.0,
            "sources": ["hiring_post_paste"],
        }
        recruiter = await persist_recruiter_discovery(
            self.db,
            job_id=str(job.id),
            discovery=discovery,
        )

        package: dict[str, Any] | None = None
        package_error: str | None = None
        if run_package:
            if not library:
                package_error = (
                    f"No base resumes in {resume_dir}. "
                    "Copy your PDF/DOCX into data/resumes/ on the host, then retry."
                )
            else:
                try:
                    print(
                        f"[quick_apply] packaging job={job.id} "
                        f"library={len(library)} files from {resume_dir}"
                    )
                    package = await ApplyPackageService(self.db).generate_for_application(
                        user_id,
                        app.id,
                        company_override=parsed.company_name,
                    )
                except HTTPException as exc:
                    package_error = str(exc.detail)
                except Exception as exc:
                    package_error = str(exc)

        app = (
            await self.db.execute(
                select(DBApplication)
                .where(DBApplication.id == app.id)
                .options(selectinload(DBApplication.job))
            )
        ).scalars().first()

        cand = (candidate_name or "").strip() or "Candidate"
        subject, body = build_interest_email(
            contact_name=name,
            role_title=parsed.role_title,
            company_name=parsed.company_name,
            candidate_name=cand,
            highlight_skills=parsed.required_skills,
            source_url=parsed.linkedin_post_url or source_url,
        )

        message = await persist_outreach_draft(
            self.db,
            job_id=str(job.id),
            draft={"subject_line": subject, "body": body},
            recruiter_id=str(recruiter.id) if recruiter else None,
        )

        resume_download = None
        if app:
            state = app.workflow_state or {}
            pkg = (
                state.get("apply_package")
                if isinstance(state.get("apply_package"), dict)
                else {}
            )
            files = pkg.get("files") or {}
            if files.get("resume_pdf") or files.get("resume_docx"):
                kind = "resume_pdf" if files.get("resume_pdf") else "resume_docx"
                resume_download = (
                    f"/api/v1/documents/package-download"
                    f"?application_id={app.id}&kind={kind}"
                )

        mailto = None
        gmail = None
        if email:
            mailto = (
                f"mailto:{quote(email)}?subject={quote(subject)}&body={quote(body)}"
            )
            gmail = (
                "https://mail.google.com/mail/?view=cm&fs=1"
                f"&to={quote(email)}&su={quote(subject)}&body={quote(body)}"
            )

        warnings = list(parsed.warnings)
        if package_error:
            warnings.append(f"Package/tailor issue: {package_error}")
        if not resume_download and not package_error:
            warnings.append(
                "No tailored resume file yet — check data/resumes/ and retry with package."
            )

        return {
            "parsed": {
                "role_title": parsed.role_title,
                "company_name": parsed.company_name,
                "contact_email": email,
                "contact_name": name,
                "linkedin_post_url": parsed.linkedin_post_url or source_url,
                "linkedin_profile_url": parsed.linkedin_profile_url,
                "required_skills": parsed.required_skills,
                "location": parsed.location,
            },
            "job_id": str(job.id),
            "application_id": str(app.id) if app else None,
            "message_id": str(message.id) if message else None,
            "recruiter_id": str(recruiter.id) if recruiter else None,
            "email_draft": {
                "to": email,
                "subject": subject,
                "body": body,
            },
            "mailto": mailto,
            "gmail_url": gmail,
            "resume_download_url": resume_download,
            "package": package,
            "resume_library_count": len(library),
            "warnings": warnings,
            "next_steps": [
                "Review / edit the email draft",
                "Click Download PDF & open Gmail (downloads resume, then opens compose)",
                "Attach the downloaded PDF in Gmail (paperclip) — browsers cannot auto-attach",
                "Send, then Mark sent on Outreach",
            ],
            "note": (
                "Gmail/mailto cannot auto-attach files. Use Download PDF & open Gmail, "
                "then attach the downloaded resume (or configure SMTP for true send)."
            ),
        }
