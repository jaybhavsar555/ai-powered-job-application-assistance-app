"""Build per-company application packages (resume + cover letter DOCX/PDF)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.application.agents.cover_letter_agent import CoverLetterAgent
from app.application.agents.resume_optimizer import ResumeOptimizerAgent
from app.application.services.document_generator import DocumentGenerator
from app.core.config import get_settings
from app.infrastructure.db.models import DBApplication, DBJob
from app.infrastructure.resume_library import (
    detect_role_family,
    extract_text,
    list_resume_files,
    missing_skills_from_job,
    parse_contact,
    pick_base_resume,
    slugify,
)


class ApplyPackageService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.docs = DocumentGenerator()
        self.resume_agent = ResumeOptimizerAgent()
        self.cover_agent = CoverLetterAgent()

    def _source_dir(self) -> Path:
        path = Path(self.settings.RESUME_SOURCE_DIR)
        if not path.exists():
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Resume source folder not found: {path}. "
                    "Put PDF/DOCX templates there or set RESUME_SOURCE_DIR."
                ),
            )
        return path

    def _package_root(self) -> Path:
        raw = (self.settings.APPLICATION_PACKAGE_DIR or "").strip()
        if not raw:
            raise HTTPException(
                status_code=400,
                detail=(
                    "APPLICATION_PACKAGE_DIR is not set. "
                    "Set it to a writable folder (e.g. ./data/packages) so "
                    "tailored packages do not pollute the resume library."
                ),
            )
        root = Path(raw)
        try:
            root.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot create package directory {root}: {e}",
            ) from e
        return root

    def library_status(self) -> dict[str, Any]:
        source = Path(self.settings.RESUME_SOURCE_DIR)
        files = list_resume_files(source) if source.exists() else []
        out = (self.settings.APPLICATION_PACKAGE_DIR or "").strip() or None
        return {
            "source_dir": str(source),
            "exists": source.exists(),
            "output_dir": out,
            "files": [
                {
                    "name": f.name,
                    "path": str(f.path),
                    "role_hint": f.role_hint,
                }
                for f in files
            ],
            "target_roles": [
                "Flutter Engineer / Developer",
                "SDE / Software Engineer",
                "Full Stack Engineer / Developer",
                "AI Engineer",
            ],
        }

    async def generate_for_application(
        self,
        user_id: UUID,
        application_id: UUID,
        company_override: Optional[str] = None,
    ) -> dict[str, Any]:
        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.id == application_id, DBApplication.user_id == user_id)
            .options(selectinload(DBApplication.job))
        )
        app = result.scalars().first()
        if not app or not app.job:
            raise HTTPException(status_code=404, detail="Application not found")
        return await self._generate(user_id=user_id, job=app.job, application=app, company_override=company_override)

    async def generate_for_job(
        self,
        user_id: UUID,
        job_id: UUID,
        company_override: Optional[str] = None,
    ) -> dict[str, Any]:
        result = await self.db.execute(
            select(DBJob).where(DBJob.id == job_id, DBJob.user_id == user_id)
        )
        job = result.scalars().first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        app_result = await self.db.execute(
            select(DBApplication).where(
                DBApplication.job_id == job.id,
                DBApplication.user_id == user_id,
            )
        )
        app = app_result.scalars().first()
        return await self._generate(user_id=user_id, job=job, application=app, company_override=company_override)

    async def _generate(
        self,
        user_id: UUID,
        job: DBJob,
        application: Optional[DBApplication],
        company_override: Optional[str],
    ) -> dict[str, Any]:
        source = self._source_dir()
        normalized = job.description_normalized or {}
        company = (
            company_override
            or normalized.get("company_name")
            or "Unknown_Company"
        )
        role_title = job.role_title or normalized.get("role_title") or "Role"
        jd = job.description_raw or ""
        required = normalized.get("required_skills") or []

        role_family = detect_role_family(role_title, jd)
        base = pick_base_resume(source, role_family)
        if not base:
            raise HTTPException(
                status_code=400,
                detail=f"No resume files found in {source}. Add PDF/DOCX templates there.",
            )

        resume_text = extract_text(base.path)
        if not resume_text or len(resume_text) < 80:
            raise HTTPException(
                status_code=400,
                detail=f"Could not extract text from {base.name}",
            )

        user_name, contact = parse_contact(resume_text)
        missing = missing_skills_from_job(required, resume_text)

        opt = await self.resume_agent.run(
            {
                "resume_json": resume_text[:12000],
                "ats_score": {"missing_skills": missing},
                "job_description": f"Company: {company}\nRole: {role_title}\n\n{jd[:8000]}",
            }
        )
        optimized = opt.get("optimized_resume") or {}

        cover = await self.cover_agent.run(
            {
                "optimized_resume": optimized,
                "job_description": f"Company: {company}\nRole: {role_title}\n\n{jd[:8000]}",
                "company_research": normalized.get("company_research")
                or f"Applying to {company} for {role_title}.",
            }
        )
        cover_payload = cover.get("cover_letter") or {}
        cover_text = cover_payload.get("content") or ""

        summary = optimized.get("summary") or ""
        bullets = optimized.get("tailored_bullets") or []
        keywords = optimized.get("added_keywords") or missing

        out_root = self._package_root()
        folder_name = slugify(str(company))
        package_dir = out_root / folder_name
        package_dir.mkdir(parents=True, exist_ok=True)

        role_slug = slugify(str(role_title), fallback=role_family)
        name_slug = slugify(user_name or "Candidate", fallback="Candidate")
        stem = f"{name_slug}_{folder_name}_{role_slug}"
        paths = {
            "resume_docx": package_dir / f"{stem}_Resume.docx",
            "resume_pdf": package_dir / f"{stem}_Resume.pdf",
            "cover_docx": package_dir / f"{stem}_Cover_Letter.docx",
            "cover_pdf": package_dir / f"{stem}_Cover_Letter.pdf",
        }

        resume_docx = self.docs.generate_resume_docx(
            user_name, contact, summary, bullets, skills=keywords, base_excerpt=resume_text[:3500]
        )
        resume_pdf, resume_tex = self.docs.generate_resume_pdf(
            user_name, contact, summary, bullets, skills=keywords, base_excerpt=resume_text[:3500]
        )
        cover_docx = self.docs.generate_cover_letter_docx(user_name, cover_text)
        cover_pdf = self.docs.generate_cover_letter_pdf(user_name, cover_text)

        paths["resume_docx"].write_bytes(resume_docx.getvalue())
        paths["resume_pdf"].write_bytes(resume_pdf.getvalue())
        
        if resume_tex:
            paths["resume_tex"] = package_dir / f"{stem}_Resume.tex"
            paths["resume_tex"].write_text(resume_tex, encoding="utf-8")
            
        paths["cover_docx"].write_bytes(cover_docx.getvalue())
        paths["cover_pdf"].write_bytes(cover_pdf.getvalue())

        package_meta = {
            "folder": str(package_dir),
            "company": company,
            "role_title": role_title,
            "role_family": role_family,
            "base_resume": str(base.path),
            "files": {k: str(v) for k, v in paths.items()},
            "summary": summary,
            "added_keywords": keywords,
            "cover_hooks": cover_payload.get("hooks_used") or [],
        }

        if application is not None:
            state = dict(application.workflow_state or {})
            state["apply_package"] = package_meta
            application.workflow_state = state
            await self.db.commit()

        return package_meta
