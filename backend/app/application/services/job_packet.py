"""
Per-job research packets for Loop Engineer v2+.

Each packet bundles JD summary, company research, tailored resume preview,
and cover letter draft so you can review before confirming apply.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm.attributes import flag_modified
import copy

from app.core.config import get_settings
from app.infrastructure.db.models import DBApplication, DBJob, DBUser
from app.infrastructure.resume_library import extract_text, list_resume_files
from app.application.agents.company_research import CompanyResearchAgent
from app.application.agents.resume_optimizer import ResumeOptimizerAgent
from app.application.agents.cover_letter_agent import CoverLetterAgent
from app.application.agents.skill_gap_agent import heuristic_skill_gap

logger = logging.getLogger(__name__)

PACKET_STATUSES = frozenset(
    {"pending_review", "confirmed", "rejected", "applied", "building", "failed"}
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _packets_root() -> Path:
    settings = get_settings()
    root = Path(getattr(settings, "LOOP_ENGINEER_DIR", None) or "./data/loop_engineer")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _user_packets_dir(user_id: UUID) -> Path:
    d = _packets_root() / str(user_id) / "packets"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _packet_path(user_id: UUID, packet_id: str) -> Path:
    return _user_packets_dir(user_id) / f"{packet_id}.json"


class JobPacketService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()
        self.company_agent = CompanyResearchAgent()
        self.resume_agent = ResumeOptimizerAgent()
        self.cover_agent = CoverLetterAgent()

    def list_packets(
        self,
        user_id: UUID,
        *,
        status: Optional[str] = None,
        run_id: Optional[str] = None,
        limit: int = 30,
    ) -> List[Dict[str, Any]]:
        files = sorted(
            _user_packets_dir(user_id).glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        out: List[Dict[str, Any]] = []
        for path in files:
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if status and data.get("status") != status:
                continue
            if run_id and data.get("run_id") != run_id:
                continue
            out.append(self._summary(data))
            if len(out) >= limit:
                break
        return out

    def get_packet(self, user_id: UUID, packet_id: str) -> Dict[str, Any]:
        path = _packet_path(user_id, packet_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Job packet not found")
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, user_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        data["updated_at"] = _utc_now_iso()
        path = _packet_path(user_id, data["id"])
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    @staticmethod
    def _summary(data: Dict[str, Any]) -> Dict[str, Any]:
        job = data.get("job") or {}
        return {
            "id": data.get("id"),
            "run_id": data.get("run_id"),
            "pipeline_job_id": data.get("pipeline_job_id"),
            "status": data.get("status"),
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "notified_at": data.get("notified_at"),
            "title": job.get("title"),
            "company": job.get("company") or job.get("company_name"),
            "url": job.get("url"),
            "match_score": job.get("matchScore") or job.get("match_score"),
            "match_reason": job.get("matchReason") or job.get("match_reason"),
            "ingested_job_id": data.get("ingested_job_id"),
            "apply_session_id": data.get("apply_session_id"),
            "build_error": data.get("build_error"),
        }

    def _resume_text(self) -> str:
        source = Path(self.settings.RESUME_SOURCE_DIR)
        files = list_resume_files(source) if source.exists() else []
        if not files:
            return "No resume on file — upload in Resumes."
        return extract_text(files[0].path)[:12000]

    def _jd_text(self, job: Dict[str, Any]) -> str:
        parts = [
            str(job.get("title") or ""),
            str(job.get("company") or job.get("company_name") or ""),
            str(job.get("full_jd") or job.get("description") or ""),
            str(job.get("matchReason") or job.get("match_reason") or ""),
        ]
        return "\n".join(p for p in parts if p.strip())

    def _jd_summary(self, job: Dict[str, Any]) -> str:
        desc = (
            job.get("full_jd")
            or job.get("description")
            or job.get("matchReason")
            or job.get("match_reason")
            or ""
        )
        clean = str(desc).strip()
        if len(clean) <= 400:
            return clean or "No JD text — open the posting URL before applying."
        return clean[:397] + "..."

    async def build_packet(
        self,
        user_id: UUID,
        *,
        job: Dict[str, Any],
        run_id: Optional[str] = None,
        pipeline_job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        packet_id = str(uuid4())
        company = (job.get("company") or job.get("company_name") or "Company").strip()
        title = (job.get("title") or "Open Role").strip()
        jd = self._jd_text(job)

        data: Dict[str, Any] = {
            "id": packet_id,
            "user_id": str(user_id),
            "run_id": run_id,
            "pipeline_job_id": pipeline_job_id or job.get("id"),
            "status": "building",
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
            "job": job,
            "jd_summary": self._jd_summary(job),
            "company_research": None,
            "tailored_resume": None,
            "cover_letter_preview": None,
            "ingested_job_id": None,
            "apply_session_id": None,
            "notified_at": None,
            "build_error": None,
        }
        self._save(user_id, data)

        try:
            research = await self.company_agent.run(
                {
                    "company": company,
                    "title": title,
                    "job_url": job.get("url"),
                    "job_details": {
                        "company_name": company,
                        "role_title": title,
                    },
                }
            )
            data["company_research"] = research.get("company_research")

            resume_text = self._resume_text()
            gap = heuristic_skill_gap(resume_text, jd)
            opt = await self.resume_agent.run(
                {
                    "resume_json": resume_text,
                    "ats_score": {"missing_skills": gap.missing_skills},
                    "job_description": jd[:12000],
                }
            )
            optimized = opt.get("optimized_resume") or {}
            data["tailored_resume"] = optimized
            data["skill_gap"] = {
                "match_score": gap.match_score,
                "missing_skills": gap.missing_skills[:12],
                "rationale": gap.rationale,
            }

            cover = await self.cover_agent.run(
                {
                    "optimized_resume": optimized,
                    "job_description": jd[:8000],
                    "company_research": data["company_research"],
                }
            )
            cover_payload = cover.get("cover_letter") or {}
            data["cover_letter_preview"] = cover_payload.get("content") or ""

            data["status"] = "pending_review"
            data["build_error"] = None
        except Exception as exc:
            logger.exception("Job packet build failed for %s at %s", company, title)
            data["status"] = "failed"
            data["build_error"] = f"{type(exc).__name__}: {exc}"

        return self._save(user_id, data)

    async def build_packets_for_run(
        self,
        user_id: UUID,
        run: Dict[str, Any],
        *,
        min_score: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        threshold = min_score
        if threshold is None:
            threshold = int(
                getattr(self.settings, "LOOP_ENGINEER_AUTO_PACKET_MIN_SCORE", 70) or 70
            )
        built: List[Dict[str, Any]] = []
        for job in run.get("jobs") or []:
            score = int(job.get("matchScore") or job.get("match_score") or 0)
            if score < threshold:
                continue
            packet = await self.build_packet(
                user_id,
                job=job,
                run_id=run.get("id"),
                pipeline_job_id=str(job.get("id")),
            )
            built.append(self._summary(packet))
        return built

    async def confirm_packet(
        self,
        user_id: UUID,
        packet_id: str,
        *,
        start_apply: bool = True,
        generate_package: Optional[bool] = None,
        sync_portfolio: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """User approved packet → ingest, package, portfolio, apply queue, apply session."""
        from app.application.services.job import JobService
        from app.application.services.apply_session import ApplySessionService
        from app.schemas.job import JobCreate
        from app.application.services.workflow_persistence import persist_company_research

        data = self.get_packet(user_id, packet_id)
        if data.get("status") not in ("pending_review", "failed"):
            raise HTTPException(
                status_code=400,
                detail=f"Packet status is {data.get('status')}, cannot confirm",
            )

        if generate_package is None:
            generate_package = bool(
                getattr(self.settings, "LOOP_ENGINEER_AUTO_PACKAGE_ON_CONFIRM", True)
            )
        if sync_portfolio is None:
            sync_portfolio = bool(
                getattr(self.settings, "LOOP_ENGINEER_SYNC_PORTFOLIO_ON_CONFIRM", True)
            )

        job = data.get("job") or {}
        url = (job.get("url") or "").strip() or None
        title = (job.get("title") or "Open Role").strip()
        company = (job.get("company") or job.get("company_name") or "").strip()
        desc = self._jd_text(job)
        if len(desc) < 80:
            desc = (
                f"{title} at {company or 'Company'}.\n\n"
                f"Source: {url or 'n/a'}\n"
                f"Confirmed via Loop Engineer job packet.\n"
                + ("x" * 40)
            )

        job_service = JobService(self.db)
        db_job = await job_service.ingest_job(
            user_id,
            JobCreate(
                url=url,
                role_title=title,
                company_name=company or None,
                description_raw=desc,
            ),
        )
        data["ingested_job_id"] = str(db_job.id)

        if data.get("company_research"):
            try:
                await persist_company_research(
                    self.db,
                    job_id=str(db_job.id),
                    research=data["company_research"],
                )
            except Exception as exc:
                logger.warning("Persist company research on confirm: %s", exc)

        result = await self.db.execute(
            select(DBApplication).where(
                DBApplication.user_id == user_id,
                DBApplication.job_id == db_job.id,
            )
        )
        app = result.scalars().first()
        if app:
            state = copy.deepcopy(dict(app.workflow_state or {}))
            if data.get("tailored_resume"):
                state["tailored_resume"] = data["tailored_resume"]
            if data.get("cover_letter_preview"):
                state["cover_letter"] = data["cover_letter_preview"]
            state["job_packet_id"] = packet_id
            state["loop_engineer_confirmed"] = True
            app.workflow_state = state
            flag_modified(app, "workflow_state")
            await self.db.flush()

        package_info: Dict[str, Any] = {}
        if generate_package and app:
            try:
                from app.application.services.apply_package import ApplyPackageService

                pkg = ApplyPackageService(self.db)
                package_info = await pkg.generate_for_application(user_id, app.id)
                await self.db.refresh(app)
            except Exception as exc:
                logger.warning("Package generation on packet confirm: %s", exc)
                package_info = {"error": str(exc)}

        portfolio_info: Dict[str, Any] = {}
        if sync_portfolio:
            try:
                from app.application.services.portfolio_export import PortfolioExportService

                email = await self.get_user_email(user_id)
                portfolio_info = PortfolioExportService().export_from_packet(
                    user_id, data, user_email=email
                )
            except Exception as exc:
                logger.warning("Portfolio export on confirm: %s", exc)
                portfolio_info = {"error": str(exc)}

        apply_session_id = None
        if start_apply and app:
            apply_svc = ApplySessionService(self.db)
            session = await apply_svc.start(user_id, job_id=db_job.id)
            apply_session_id = str(session.get("id") or "")
            data["apply_session_id"] = apply_session_id

        # v5 — extension apply queue for autofill on job URL
        queue_entry: Dict[str, Any] = {}
        if app:
            try:
                from app.application.services.extension_apply_queue import enqueue

                state = app.workflow_state or {}
                pkg = state.get("apply_package") if isinstance(state.get("apply_package"), dict) else {}
                files = pkg.get("files") or {}
                queue_entry = enqueue(
                    user_id,
                    application_id=str(app.id),
                    job_id=str(db_job.id),
                    url=url,
                    company=company or "Company",
                    title=title,
                    packet_id=packet_id,
                    package_files=files,
                )
            except Exception as exc:
                logger.warning("Extension queue enqueue: %s", exc)

        data["status"] = "confirmed"
        await self.db.commit()
        saved = self._save(user_id, data)
        return {
            "packet": self._summary(saved),
            "ingested_job_id": saved.get("ingested_job_id"),
            "apply_session_id": apply_session_id,
            "apply_href": f"/apply?job_id={saved.get('ingested_job_id')}",
            "package": package_info,
            "portfolio": portfolio_info,
            "extension_queue": queue_entry,
            "message": (
                "Confirmed — package generated, portfolio updated, Review & Apply started. "
                "Open the job URL with the Chrome extension to autofill."
            ),
        }

    def reject_packet(self, user_id: UUID, packet_id: str) -> Dict[str, Any]:
        data = self.get_packet(user_id, packet_id)
        if data.get("status") != "pending_review":
            raise HTTPException(
                status_code=400,
                detail=f"Packet status is {data.get('status')}, cannot reject",
            )
        data["status"] = "rejected"
        return {"packet": self._summary(self._save(user_id, data))}

    async def batch_confirm(
        self,
        user_id: UUID,
        packet_ids: List[str],
        *,
        start_apply: bool = True,
    ) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, str]] = []
        for pid in packet_ids or []:
            try:
                out = await self.confirm_packet(
                    user_id, pid, start_apply=start_apply
                )
                results.append(out)
            except HTTPException as exc:
                errors.append({"packet_id": pid, "detail": str(exc.detail)})
            except Exception as exc:
                errors.append({"packet_id": pid, "detail": str(exc)})
        return {
            "confirmed": len(results),
            "errors": errors,
            "results": results,
        }

    def batch_reject(self, user_id: UUID, packet_ids: List[str]) -> Dict[str, Any]:
        rejected = 0
        errors: List[Dict[str, str]] = []
        for pid in packet_ids or []:
            try:
                self.reject_packet(user_id, pid)
                rejected += 1
            except HTTPException as exc:
                errors.append({"packet_id": pid, "detail": str(exc.detail)})
        return {"rejected": rejected, "errors": errors}

    def mark_notified(self, user_id: UUID, packet_ids: List[str]) -> None:
        now = _utc_now_iso()
        for pid in packet_ids:
            path = _packet_path(user_id, pid)
            if not path.exists():
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            data["notified_at"] = now
            self._save(user_id, data)

    async def get_user_email(self, user_id: UUID) -> Optional[str]:
        user = await self.db.get(DBUser, user_id)
        return (user.email if user else None) or None
