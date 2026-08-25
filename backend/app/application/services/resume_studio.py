"""Resume Studio: versions, side-by-side compare, package download metadata."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.infrastructure.db.models import DBApplication, DBJob, DBResumeVersion
from app.infrastructure.resume_library import extract_text


PACKAGE_KINDS = ("resume_pdf", "resume_docx", "resume_tex", "cover_pdf", "cover_docx")


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
