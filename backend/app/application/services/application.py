from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from typing import List
from fastapi import HTTPException
from app.infrastructure.db.models import DBApplication, DBJob
from app.schemas.application import ApplicationCreate, APPLICATION_STAGES
from app.application.services.follow_up import schedule_follow_up_on_applied


class ApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _to_response(self, app: DBApplication) -> dict:
        job = app.job
        company_name = None
        required_skills: List[str] = []
        if job and job.description_normalized:
            company_name = job.description_normalized.get("company_name")
            required_skills = job.description_normalized.get("required_skills") or []

        return {
            "id": app.id,
            "user_id": app.user_id,
            "job_id": app.job_id,
            "stage": app.stage,
            "workflow_state": app.workflow_state or {},
            "created_at": app.created_at,
            "updated_at": app.updated_at,
            "job": {
                "id": job.id,
                "role_title": job.role_title,
                "url": job.url,
                "status": job.status,
                "company_name": company_name,
                "required_skills": required_skills,
            } if job else None,
        }

    async def list_by_user(self, user_id: UUID) -> List[dict]:
        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.user_id == user_id)
            .options(selectinload(DBApplication.job))
            .order_by(DBApplication.updated_at.desc())
        )
        return [self._to_response(app) for app in result.scalars().all()]

    async def get_by_id(self, user_id: UUID, application_id: UUID) -> dict:
        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.id == application_id, DBApplication.user_id == user_id)
            .options(selectinload(DBApplication.job))
        )
        app = result.scalars().first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")
        return self._to_response(app)

    async def create(self, user_id: UUID, data: ApplicationCreate) -> dict:
        job_result = await self.db.execute(
            select(DBJob).where(DBJob.id == data.job_id, DBJob.user_id == user_id)
        )
        job = job_result.scalars().first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        existing = await self.db.execute(
            select(DBApplication).where(DBApplication.job_id == data.job_id)
        )
        if existing.scalars().first():
            raise HTTPException(status_code=409, detail="Application already exists for this job")

        stage = data.stage if data.stage in APPLICATION_STAGES else "Wishlist"
        app = DBApplication(
            user_id=user_id,
            job_id=data.job_id,
            stage=stage,
            workflow_state={},
        )
        self.db.add(app)
        await self.db.commit()

        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.id == app.id)
            .options(selectinload(DBApplication.job))
        )
        return self._to_response(result.scalars().one())

    async def create_for_job(self, user_id: UUID, job_id: UUID, stage: str = "Wishlist") -> DBApplication:
        """Internal helper used when ingesting a job."""
        app = DBApplication(
            user_id=user_id,
            job_id=job_id,
            stage=stage if stage in APPLICATION_STAGES else "Wishlist",
            workflow_state={},
        )
        self.db.add(app)
        return app

    async def update_stage(self, user_id: UUID, application_id: UUID, stage: str) -> dict:
        if stage not in APPLICATION_STAGES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage. Must be one of: {', '.join(APPLICATION_STAGES)}",
            )

        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.id == application_id, DBApplication.user_id == user_id)
            .options(selectinload(DBApplication.job))
        )
        app = result.scalars().first()
        if not app:
            raise HTTPException(status_code=404, detail="Application not found")

        previous = app.stage
        app.stage = stage
        await self.db.commit()
        await self.db.refresh(app)

        follow_up_meta = None
        if stage == "Applied" and previous != "Applied":
            follow_up_meta = await schedule_follow_up_on_applied(self.db, app)

        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.id == application_id, DBApplication.user_id == user_id)
            .options(selectinload(DBApplication.job))
        )
        app = result.scalars().one()
        payload = self._to_response(app)
        if follow_up_meta:
            payload["follow_up"] = follow_up_meta
        return payload
