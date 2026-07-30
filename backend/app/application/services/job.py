from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List
from fastapi import HTTPException
from app.infrastructure.db.models import DBJob, DBApplication
from app.infrastructure.scraping import scrape_job_page
from app.schemas.job import JobCreate
from app.application.agents.job_intake import JobIntakeAgent


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent = JobIntakeAgent()

    async def ingest_job(self, user_id: UUID, data: JobCreate) -> DBJob:
        if not data.url and not (data.description_raw and data.description_raw.strip()):
            raise HTTPException(
                status_code=400,
                detail="Provide a job url and/or description_raw",
            )

        scrape_source = "provided"
        scrape_error = None
        title = data.role_title or ""
        company = data.company_name or ""

        if data.description_raw and data.description_raw.strip():
            raw_text = data.description_raw.strip()
        else:
            scraped = await scrape_job_page(str(data.url))
            raw_text = scraped.text
            scrape_source = scraped.source
            scrape_error = scraped.error
            if not title and scraped.title:
                title = scraped.title
            if not company and scraped.company:
                company = scraped.company
            print(
                f"[JobService] scrape url={data.url} source={scrape_source} "
                f"chars={len(raw_text)} error={scrape_error}"
            )

        normalized = await self.agent.extract_and_normalize(
            raw_description=raw_text,
            title=title,
            company=company,
        )

        job = DBJob(
            user_id=user_id,
            url=str(data.url) if data.url else None,
            role_title=normalized.role_title,
            description_raw=raw_text,
            description_normalized={
                **normalized.model_dump(),
                "_scrape": {
                    "source": scrape_source,
                    "error": scrape_error,
                },
            },
            status="Imported",
        )
        self.db.add(job)
        await self.db.flush()

        self.db.add(
            DBApplication(
                user_id=user_id,
                job_id=job.id,
                stage="Wishlist",
                workflow_state={"scrape_source": scrape_source},
            )
        )

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
