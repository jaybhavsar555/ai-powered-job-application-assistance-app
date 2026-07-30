from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List
from fastapi import HTTPException
from app.infrastructure.db.models import DBJob, DBApplication
from app.schemas.job import JobCreate
from app.application.agents.job_intake import JobIntakeAgent

class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent = JobIntakeAgent()

    async def ingest_job(self, user_id: UUID, data: JobCreate) -> DBJob:
        # If a URL is provided but no raw description, we would scrape it here.
        # For MVP, we assume raw_description is passed or we mock the scraping.
        raw_text = data.description_raw or f"Simulated scrape of {data.url}"
        
        # Call the Agent to normalize the unstructured text
        normalized = await self.agent.extract_and_normalize(
            raw_description=raw_text,
            title=data.role_title or "",
            company=data.company_name or ""
        )
        
        # Create the Job record
        job = DBJob(
            user_id=user_id,
            url=str(data.url) if data.url else None,
            role_title=normalized.role_title,
            description_raw=raw_text,
            description_normalized=normalized.model_dump(),
            status="Imported"
        )
        self.db.add(job)
        await self.db.flush()

        # Auto-create a Wishlist application for the Kanban tracker
        self.db.add(DBApplication(
            user_id=user_id,
            job_id=job.id,
            stage="Wishlist",
            workflow_state={},
        ))

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def list_by_user(self, user_id: UUID) -> List[DBJob]:
        result = await self.db.execute(
            select(DBJob).where(DBJob.user_id == user_id).order_by(DBJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, user_id: UUID, job_id: UUID) -> DBJob:
        result = await self.db.execute(
            select(DBJob).where(DBJob.id == job_id, DBJob.user_id == user_id)
        )
        job = result.scalars().first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
