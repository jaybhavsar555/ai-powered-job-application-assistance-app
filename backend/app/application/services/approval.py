from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.infrastructure.db.models import (
    DBApplication,
    DBJob,
    DBCoverLetter,
    DBResumeVersion,
)
from app.schemas.approval import ApprovalDecisionRequest, ApprovalDecisionResponse


class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_application(
        self,
        user_id: UUID,
        *,
        application_id: Optional[UUID],
        job_id: Optional[UUID],
    ) -> DBApplication:
        if application_id:
            result = await self.db.execute(
                select(DBApplication)
                .where(DBApplication.id == application_id, DBApplication.user_id == user_id)
                .options(selectinload(DBApplication.job))
            )
            app = result.scalars().first()
            if not app:
                raise HTTPException(status_code=404, detail="Application not found")
            return app

        if job_id:
            result = await self.db.execute(
                select(DBApplication)
                .where(DBApplication.job_id == job_id, DBApplication.user_id == user_id)
                .options(selectinload(DBApplication.job))
            )
            app = result.scalars().first()
            if app:
                return app

            # Ensure job exists (demo workflow may use a placeholder UUID)
            job_result = await self.db.execute(
                select(DBJob).where(DBJob.id == job_id, DBJob.user_id == user_id)
            )
            job = job_result.scalars().first()
            if not job:
                job = DBJob(
                    id=job_id,
                    user_id=user_id,
                    role_title="Demo Software Engineer",
                    description_raw="Created automatically for workflow approval demo.",
                    description_normalized={
                        "role_title": "Demo Software Engineer",
                        "company_name": "Demo Corp",
                        "required_skills": ["Python", "FastAPI"],
                    },
                    status="Imported",
                )
                self.db.add(job)
                await self.db.flush()

            app = DBApplication(
                user_id=user_id,
                job_id=job.id,
                stage="Researching",
                workflow_state={"source": "approval_bootstrap"},
            )
            self.db.add(app)
            await self.db.flush()
            await self.db.refresh(app)
            return app

        raise HTTPException(
            status_code=400,
            detail="Provide application_id or job_id to resolve the approval target",
        )

    async def decide(
        self, user_id: UUID, data: ApprovalDecisionRequest
    ) -> ApprovalDecisionResponse:
        app = await self._resolve_application(
            user_id,
            application_id=data.application_id,
            job_id=data.job_id,
        )

        state: Dict[str, Any] = dict(app.workflow_state or {})
        approvals: Dict[str, Any] = dict(state.get("approvals") or {})
        now = datetime.utcnow()

        cover_letter_id = None
        resume_version_id = None
        message = ""

        if data.artifact == "cover_letter":
            if data.decision == "approve":
                content = (data.cover_letter or "").strip()
                if not content:
                    raise HTTPException(status_code=400, detail="cover_letter content is required to approve")
                letter = DBCoverLetter(
                    application_id=app.id,
                    content_md=content,
                    letter_type="AI-Tailored",
                )
                self.db.add(letter)
                await self.db.flush()
                cover_letter_id = letter.id
                approvals["cover_letter"] = {
                    "status": "approved",
                    "at": now.isoformat(),
                    "cover_letter_id": str(letter.id),
                    "evidence": data.evidence,
                }
                message = "Cover letter approved and saved"
            else:
                approvals["cover_letter"] = {
                    "status": "rejected",
                    "at": now.isoformat(),
                    "evidence": data.evidence,
                }
                message = "Cover letter rejected"

        elif data.artifact == "resume":
            if data.decision == "approve":
                tailored = data.tailored_resume or {}
                if not tailored:
                    raise HTTPException(status_code=400, detail="tailored_resume is required to approve")
                version = DBResumeVersion(
                    application_id=app.id,
                    base_resume_id=None,
                    tailored_content=tailored,
                    ats_score=data.ats_score,
                    feedback=[{"evidence": data.evidence}] if data.evidence else [],
                )
                self.db.add(version)
                await self.db.flush()
                resume_version_id = version.id
                approvals["resume"] = {
                    "status": "approved",
                    "at": now.isoformat(),
                    "resume_version_id": str(version.id),
                    "evidence": data.evidence,
                }
                message = "Resume optimization approved and saved as a new version"
            else:
                approvals["resume"] = {
                    "status": "rejected",
                    "at": now.isoformat(),
                    "evidence": data.evidence,
                }
                message = "Resume optimization rejected"

        state["approvals"] = approvals
        state["last_decision_at"] = now.isoformat()

        both_approved = (
            isinstance(approvals.get("cover_letter"), dict)
            and approvals["cover_letter"].get("status") == "approved"
            and isinstance(approvals.get("resume"), dict)
            and approvals["resume"].get("status") == "approved"
        )
        if both_approved:
            state["requires_human_approval"] = False

        app.workflow_state = state

        # Advance pipeline when at least one artifact is approved and none pending reject-all
        approved_any = any(
            v.get("status") == "approved" for v in approvals.values() if isinstance(v, dict)
        )
        if approved_any and app.stage in ("Wishlist", "Researching"):
            app.stage = "Ready"

        await self.db.commit()
        await self.db.refresh(app)

        return ApprovalDecisionResponse(
            application_id=app.id,
            job_id=app.job_id,
            artifact=data.artifact,
            decision=data.decision,
            stage=app.stage,
            cover_letter_id=cover_letter_id,
            resume_version_id=resume_version_id,
            message=message,
            decided_at=now,
        )
