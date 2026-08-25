"""Resume Studio: versions, side-by-side compare, package download metadata."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.application.services.ats_service import ATSService
from app.application.services.resume_parser import structured_resume_to_text
from app.core.config import get_settings
from app.infrastructure.db.models import DBApplication, DBJob, DBResumeVersion
from app.infrastructure.resume_library import extract_text


PACKAGE_KINDS = ("resume_pdf", "resume_docx", "resume_tex", "cover_pdf", "cover_docx")


def _guess_role_title(job_description: str, override: Optional[str] = None) -> str:
    if override and override.strip():
        return override.strip()[:120]
    jd = job_description or ""
    for pattern in (
        r"(?:role|position|title)\s*[:\-]\s*([^\n]{4,80})",
        r"(?:hiring|seeking)\s+(?:a\s+)?([A-Z][^\n,.]{4,60})",
        r"^([A-Z][a-zA-Z /]+(?:Engineer|Developer|Manager|Analyst|Designer|Architect))",
    ):
        match = re.search(pattern, jd, re.I | re.M)
        if match:
            return match.group(1).strip()[:120]
    return "Open Role"


def _guess_company_name(job_description: str, override: Optional[str] = None) -> str:
    if override and override.strip():
        return override.strip()[:120]
    jd = job_description or ""
    for pattern in (
        r"(?:company|employer|organization)\s*[:\-]\s*([^\n]{2,80})",
        r"(?:at|join)\s+([A-Z][A-Za-z0-9&.\- ]{2,50})(?:\s+is|\s+we|\s+are|\s*,)",
        r"^([A-Z][A-Za-z0-9&.\- ]{2,50})\s+is (?:hiring|looking)",
    ):
        match = re.search(pattern, jd, re.I | re.M)
        if match:
            return match.group(1).strip()[:120]
    return "Tailor Import"


def _company_name(job: Optional[DBJob]) -> str:
    if not job:
        return "Unknown"
    if job.company and job.company.name:
        return job.company.name
    normalized = job.description_normalized or {}
    return str(normalized.get("company_name") or "Unknown")


def _preview_tailored(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content[:4000]
    if isinstance(content, dict):
        parts: list[str] = []
        for key in ("summary", "professional_summary", "headline"):
            if content.get(key):
                parts.append(str(content[key]))
        bullets = content.get("bullets") or content.get("experience") or []
        if isinstance(bullets, list):
            for b in bullets[:12]:
                if isinstance(b, dict):
                    parts.append(str(b.get("text") or b.get("bullet") or b))
                else:
                    parts.append(str(b))
        skills = content.get("added_keywords") or content.get("skills") or []
        if skills:
            parts.append("Keywords: " + ", ".join(str(s) for s in skills[:20]))
        if parts:
            return "\n".join(parts)[:4000]
        import json

        return json.dumps(content, indent=2)[:4000]
    return str(content)[:4000]


def _package_file_flags(pkg: dict[str, Any]) -> dict[str, bool]:
    files = pkg.get("files") or {}
    flags: dict[str, bool] = {}
    for kind in PACKAGE_KINDS:
        path = files.get(kind)
        flags[kind] = bool(path and Path(str(path)).is_file())
    return flags


def _allowed_roots() -> list[Path]:
    settings = get_settings()
    roots: list[Path] = []
    for raw in (settings.APPLICATION_PACKAGE_DIR, settings.RESUME_SOURCE_DIR):
        if not raw:
            continue
        try:
            roots.append(Path(raw).resolve())
        except OSError:
            continue
    return roots


def _safe_package_path(raw: str) -> Path:
    path = Path(raw).resolve()
    roots = _allowed_roots()
    if not roots:
        raise HTTPException(status_code=400, detail="Package directories are not configured")
    if not any(path == root or root in path.parents for root in roots):
        raise HTTPException(status_code=403, detail="File path is outside allowed package dirs")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Package file not found on disk")
    return path


class ResumeStudioService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_studio(self, user_id: UUID) -> dict[str, Any]:
        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.user_id == user_id)
            .options(
                selectinload(DBApplication.job).selectinload(DBJob.company),
                selectinload(DBApplication.resume_versions),
            )
            .order_by(DBApplication.updated_at.desc())
        )
        apps = list(result.scalars().all())
        items: list[dict[str, Any]] = []
        seen_apps_with_version: set[UUID] = set()

        for app in apps:
            job = app.job
            company = _company_name(job)
            role = job.role_title if job else "Open role"
            state = app.workflow_state or {}
            pkg = state.get("apply_package") if isinstance(state.get("apply_package"), dict) else {}
            versions = sorted(
                app.resume_versions or [],
                key=lambda v: v.created_at or v.updated_at,
                reverse=True,
            )

            for ver in versions:
                seen_apps_with_version.add(app.id)
                ats = ver.ats_score
                if ats is None and state.get("ats_score") is not None:
                    try:
                        ats = int(state.get("ats_score"))
                    except (TypeError, ValueError):
                        ats = None
                items.append(
                    self._item(
                        item_id=str(ver.id),
                        source="resume_version",
                        version_id=str(ver.id),
                        application_id=str(app.id),
                        job_id=str(job.id) if job else str(app.job_id),
                        company=company,
                        role_title=role,
                        stage=app.stage or "Wishlist",
                        ats_score=ats,
                        missing_skills=list(state.get("missing_skills") or []),
                        matching_skills=list(state.get("matching_skills") or []),
                        recommendation=state.get("ats_recommendation"),
                        created_at=ver.created_at.isoformat() if ver.created_at else None,
                        approved=True,
                        package=pkg,
                        tailored_preview=_preview_tailored(ver.tailored_content),
                        added_keywords=list(
                            (ver.tailored_content or {}).get("added_keywords") or []
                            if isinstance(ver.tailored_content, dict)
                            else []
                        ),
                    )
                )

            # Draft from workflow (not yet approved as a version)
            if app.id not in seen_apps_with_version and (
                state.get("tailored_resume") or pkg or state.get("ats_score") is not None
            ):
                ats = state.get("ats_score")
                try:
                    ats_i = int(ats) if ats is not None else None
                except (TypeError, ValueError):
                    ats_i = None
                tailored = state.get("tailored_resume") or {}
                items.append(
                    self._item(
                        item_id=f"app-{app.id}",
                        source="workflow_draft",
                        version_id=None,
                        application_id=str(app.id),
                        job_id=str(job.id) if job else str(app.job_id),
                        company=company,
                        role_title=role,
                        stage=app.stage or "Wishlist",
                        ats_score=ats_i,
                        missing_skills=list(state.get("missing_skills") or []),
                        matching_skills=list(state.get("matching_skills") or []),
                        recommendation=state.get("ats_recommendation"),
                        created_at=app.updated_at.isoformat() if app.updated_at else None,
                        approved=False,
                        package=pkg,
                        tailored_preview=_preview_tailored(tailored),
                        added_keywords=list(
                            tailored.get("added_keywords") or []
                            if isinstance(tailored, dict)
                            else []
                        ),
                        tailor_source=(state.get("tailor_meta") or {}).get("source"),
                    )
                )

        return {"items": items, "count": len(items)}

    def _item(self, **kwargs: Any) -> dict[str, Any]:
        pkg = kwargs.pop("package") or {}
        item_id = kwargs.pop("item_id")
        has_package = bool(pkg.get("files")) and any(_package_file_flags(pkg).values())
        return {
            "id": item_id,
            **kwargs,
            "has_package": has_package,
            "package": {
                "folder": pkg.get("folder"),
                "company": pkg.get("company"),
                "role_family": pkg.get("role_family"),
                "base_resume_name": Path(str(pkg["base_resume"])).name
                if pkg.get("base_resume")
                else None,
                "files": _package_file_flags(pkg),
            }
            if pkg
            else None,
        }

    async def get_studio_detail(self, user_id: UUID, item_id: str) -> dict[str, Any]:
        version: Optional[DBResumeVersion] = None
        app: Optional[DBApplication] = None

        if item_id.startswith("app-"):
            try:
                app_uuid = UUID(item_id[4:])
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid studio item id") from exc
            app = await self._get_app(user_id, app_uuid)
        else:
            try:
                ver_uuid = UUID(item_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid studio item id") from exc
            result = await self.db.execute(
                select(DBResumeVersion)
                .where(DBResumeVersion.id == ver_uuid)
                .options(
                    selectinload(DBResumeVersion.application)
                    .selectinload(DBApplication.job)
                    .selectinload(DBJob.company),
                )
            )
            version = result.scalars().first()
            if not version or not version.application or version.application.user_id != user_id:
                raise HTTPException(status_code=404, detail="Resume version not found")
            app = version.application

        assert app is not None
        job = app.job
        state = app.workflow_state or {}
        pkg = state.get("apply_package") if isinstance(state.get("apply_package"), dict) else {}

        tailored = (
            version.tailored_content
            if version and version.tailored_content
            else state.get("tailored_resume") or {}
        )
        ats = version.ats_score if version and version.ats_score is not None else state.get("ats_score")
        try:
            ats_i = int(ats) if ats is not None else None
        except (TypeError, ValueError):
            ats_i = None

        original_text = ""
        original_label = "Base resume"
        base_path = pkg.get("base_resume")
        if base_path and Path(str(base_path)).is_file():
            original_label = Path(str(base_path)).name
            try:
                original_text = extract_text(Path(str(base_path)))[:8000]
            except Exception:
                original_text = ""

        if not original_text:
            # Fall back to first library file name only (no fake content)
            original_text = (
                "Original base resume text is unavailable. "
                "Generate an apply package to lock the base file used for this job."
            )

        list_payload = await self.list_studio(user_id)
        summary = next((i for i in list_payload["items"] if i["id"] == item_id), None)
        if summary is None:
            # Build minimal summary if list filtering missed (e.g. empty tailored)
            summary = self._item(
                item_id=item_id,
                source="resume_version" if version else "workflow_draft",
                version_id=str(version.id) if version else None,
                application_id=str(app.id),
                job_id=str(job.id) if job else str(app.job_id),
                company=_company_name(job),
                role_title=job.role_title if job else "Open role",
                stage=app.stage or "Wishlist",
                ats_score=ats_i,
                missing_skills=list(state.get("missing_skills") or []),
                matching_skills=list(state.get("matching_skills") or []),
                recommendation=state.get("ats_recommendation"),
                created_at=(
                    version.created_at.isoformat()
                    if version and version.created_at
                    else (app.updated_at.isoformat() if app.updated_at else None)
                ),
                approved=bool(version),
                package=pkg,
                tailored_preview=_preview_tailored(tailored),
                added_keywords=list(
                    tailored.get("added_keywords") or [] if isinstance(tailored, dict) else []
                ),
            )
            summary["id"] = item_id

        return {
            **summary,
            "original": {
                "label": original_label,
                "text": original_text,
            },
            "tailored": {
                "content": tailored if isinstance(tailored, dict) else {"text": tailored},
                "preview": _preview_tailored(tailored),
            },
            "ats": {
                "score": ats_i,
                "missing_skills": list(state.get("missing_skills") or []),
                "matching_skills": list(state.get("matching_skills") or []),
                "recommendation": state.get("ats_recommendation"),
                "added_keywords": list(
                    tailored.get("added_keywords") or [] if isinstance(tailored, dict) else []
                ),
                "parser_checks": state.get("ats_parser"),
                "rationale": state.get("ats_rationale"),
                "qualifications_match": state.get("qualifications_match"),
            },
            "downloads": {
                kind: f"/api/v1/documents/package-download?application_id={app.id}&kind={kind}"
                for kind, exists in _package_file_flags(pkg).items()
                if exists
            },
        }

    async def resolve_package_file(
        self, user_id: UUID, application_id: UUID, kind: str
    ) -> Path:
        if kind not in PACKAGE_KINDS:
            raise HTTPException(status_code=400, detail=f"kind must be one of {PACKAGE_KINDS}")
        app = await self._get_app(user_id, application_id)
        state = app.workflow_state or {}
        pkg = state.get("apply_package") if isinstance(state.get("apply_package"), dict) else {}
        files = pkg.get("files") or {}
        raw = files.get(kind)
        if not raw:
            raise HTTPException(
                status_code=404,
                detail="No successful package file for this kind — run Package after approvals",
            )
        return _safe_package_path(str(raw))

    async def _get_app(self, user_id: UUID, application_id: UUID) -> DBApplication:
        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.id == application_id, DBApplication.user_id == user_id)
            .options(
                selectinload(DBApplication.job).selectinload(DBJob.company),
                selectinload(DBApplication.resume_versions),
            )
        )
        app = result.scalars().first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        return app

    async def delete_studio_item(self, user_id: UUID, item_id: str) -> None:
        if item_id.startswith("app-"):
            try:
                app_uuid = UUID(item_id[4:])
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid studio item id") from exc
            app = await self._get_app(user_id, app_uuid)
            state = dict(app.workflow_state or {})
            if "tailored_resume" in state:
                del state["tailored_resume"]
            if "apply_package" in state:
                del state["apply_package"]
            app.workflow_state = state
            await self.db.commit()
        else:
            try:
                ver_uuid = UUID(item_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail="Invalid studio item id") from exc
            result = await self.db.execute(
                select(DBResumeVersion)
                .where(DBResumeVersion.id == ver_uuid)
                .options(selectinload(DBResumeVersion.application))
            )
            version = result.scalars().first()
            if not version or not version.application or version.application.user_id != user_id:
                raise HTTPException(status_code=404, detail="Resume version not found")
            await self.db.delete(version)
            await self.db.commit()

    async def save_tailor_run(
        self,
        user_id: UUID,
        *,
        job_description: str,
        tailored_resume: dict[str, Any],
        base_resume: str,
        job_url: Optional[str] = None,
        company_name: Optional[str] = None,
        role_title: Optional[str] = None,
        before_score: Optional[int] = None,
        after_score: Optional[int] = None,
        unified_ats: Optional[dict[str, Any]] = None,
        job_id: Optional[UUID] = None,
        application_id: Optional[UUID] = None,
        approve_version: bool = False,
    ) -> dict[str, Any]:
        """Persist a standalone Tailor run as a workflow draft (optional approved version)."""
        if not tailored_resume:
            raise HTTPException(status_code=422, detail="tailored_resume is required")
        if not (job_description or "").strip():
            raise HTTPException(status_code=422, detail="job_description is required")

        company = _guess_company_name(job_description, company_name)
        role = _guess_role_title(job_description, role_title)

        job: Optional[DBJob] = None
        app: Optional[DBApplication] = None

        if job_id:
            result = await self.db.execute(
                select(DBJob).where(DBJob.id == job_id, DBJob.user_id == user_id)
            )
            job = result.scalars().first()
            if not job:
                raise HTTPException(status_code=404, detail="Job not found")

        if application_id:
            app = await self._get_app(user_id, application_id)
            job = app.job

        if not job:
            if job_url:
                result = await self.db.execute(
                    select(DBJob).where(DBJob.user_id == user_id, DBJob.url == job_url)
                )
                job = result.scalars().first()
            if not job:
                job = DBJob(
                    id=uuid4(),
                    user_id=user_id,
                    url=job_url,
                    role_title=role,
                    description_raw=job_description[:20000],
                    description_normalized={
                        "company_name": company,
                        "role_title": role,
                    },
                    status="Imported",
                )
                self.db.add(job)
                await self.db.flush()

        if not app:
            result = await self.db.execute(
                select(DBApplication).where(
                    DBApplication.job_id == job.id,
                    DBApplication.user_id == user_id,
                )
            )
            app = result.scalars().first()
            if not app:
                app = DBApplication(
                    user_id=user_id,
                    job_id=job.id,
                    stage="Researching",
                    workflow_state={},
                )
                self.db.add(app)
                await self.db.flush()

        ats_service = ATSService()
        if unified_ats:
            from app.schemas.ats import UnifiedATSResult

            unified = UnifiedATSResult.model_validate(unified_ats)
        else:
            resume_text = structured_resume_to_text(tailored_resume)
            unified = await ats_service.analyze(
                resume_text,
                job_description,
                structured_content=tailored_resume,
            )

        state = dict(app.workflow_state or {})
        state.update(unified.to_workflow_state())
        state["tailored_resume"] = tailored_resume
        state["tailor_meta"] = {
            "source": "tailor_page",
            "base_resume": base_resume,
            "job_url": job_url,
            "before_score": before_score,
            "after_score": after_score or unified.score,
            "saved_at": datetime.utcnow().isoformat(),
        }
        app.workflow_state = state
        app.stage = app.stage or "Researching"
        app.updated_at = datetime.utcnow()

        version_id: Optional[str] = None
        if approve_version:
            ver = DBResumeVersion(
                application_id=app.id,
                tailored_content=tailored_resume,
                ats_score=unified.score,
                feedback=[{"evidence": unified.recommendation, "source": "tailor_save"}],
            )
            self.db.add(ver)
            await self.db.flush()
            version_id = str(ver.id)

        await self.db.commit()

        item_id = version_id or f"app-{app.id}"
        return {
            "item_id": item_id,
            "application_id": str(app.id),
            "job_id": str(job.id),
            "ats_score": unified.score,
            "approved": bool(version_id),
            "company": company,
            "role_title": role,
        }

    async def update_studio_content(
        self,
        user_id: UUID,
        item_id: str,
        *,
        tailored_resume: dict[str, Any],
        rescore: bool = True,
    ) -> dict[str, Any]:
        """Update tailored content on a draft or version; optionally re-run unified ATS."""
        if not tailored_resume:
            raise HTTPException(status_code=422, detail="tailored_resume is required")

        version: Optional[DBResumeVersion] = None
        app: Optional[DBApplication] = None

        if item_id.startswith("app-"):
            app_uuid = UUID(item_id[4:])
            app = await self._get_app(user_id, app_uuid)
        else:
            ver_uuid = UUID(item_id)
            result = await self.db.execute(
                select(DBResumeVersion)
                .where(DBResumeVersion.id == ver_uuid)
                .options(selectinload(DBResumeVersion.application).selectinload(DBApplication.job))
            )
            version = result.scalars().first()
            if not version or not version.application or version.application.user_id != user_id:
                raise HTTPException(status_code=404, detail="Resume version not found")
            app = version.application

        job = app.job
        jd = (job.description_raw if job else "") or ""

        unified = None
        if rescore and jd.strip():
            ats_service = ATSService()
            resume_text = structured_resume_to_text(tailored_resume)
            unified = await ats_service.analyze(
                resume_text, jd, structured_content=tailored_resume
            )

        if version:
            version.tailored_content = tailored_resume
            if unified:
                version.ats_score = unified.score
            version.updated_at = datetime.utcnow()

        state = dict(app.workflow_state or {})
        state["tailored_resume"] = tailored_resume
        if unified:
            state.update(unified.to_workflow_state())
        app.workflow_state = state
        app.updated_at = datetime.utcnow()

        await self.db.commit()

        return {
            "item_id": item_id,
            "ats_score": unified.score if unified else state.get("ats_score"),
            "unified_ats": unified.to_api_payload() if unified else None,
        }
