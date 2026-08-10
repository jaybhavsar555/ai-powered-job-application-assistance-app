from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional
from fastapi import HTTPException
from app.infrastructure.db.models import DBJob, DBApplication
from app.infrastructure.scraping import scrape_job_page
from app.schemas.job import JobCreate
from app.application.agents.job_intake import JobIntakeAgent
from app.application.services.job_urls import clean_role_title, normalize_job_url


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.agent = JobIntakeAgent()

    async def ingest_job(self, user_id: UUID, data: JobCreate) -> DBJob:
        url = normalize_job_url(data.url)
        raw_desc = (data.description_raw or "").strip()
        if not url and not raw_desc:
            raise HTTPException(
                status_code=400,
                detail="Provide a job url and/or description_raw",
            )

        if url:
            existing = await self._find_by_url(user_id, url)
            if existing:
                return existing

        scrape_source = "provided"
        scrape_error = None
        title = clean_role_title(data.role_title, default="")
        company = (data.company_name or "").strip()

        if raw_desc:
            raw_text = raw_desc
        elif url:
            scraped = await scrape_job_page(url)
            raw_text = scraped.text
            scrape_source = scraped.source
            scrape_error = scraped.error
            if not title and scraped.title:
                title = clean_role_title(scraped.title, default="")
            if not company and scraped.company:
                company = scraped.company
            print(
                f"[JobService] scrape url={url} source={scrape_source} "
                f"chars={len(raw_text)} error={scrape_error}"
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid or missing job URL — paste a full https:// link or the JD text",
            )

        normalized = await self.agent.extract_and_normalize(
            raw_description=raw_text,
            title=title,
            company=company,
        )

        role_title = clean_role_title(
            normalized.role_title,
            title,
            data.role_title,
            default="Open Role",
        )
        # Prefer user/source company over LLM when provided
        if company and not (normalized.company_name or "").strip():
            normalized.company_name = company
        elif company and company.lower() not in (
            (normalized.company_name or "").lower(),
            "",
        ):
            # Keep intake company if strong; else force provided
            if len(company) >= 2:
                normalized.company_name = company

        job = DBJob(
            user_id=user_id,
            url=url,
            role_title=role_title,
            description_raw=raw_text,
            description_normalized={
                **normalized.model_dump(),
                "role_title": role_title,
                "_scrape": {
                    "source": scrape_source,
                    "error": scrape_error,
                    "has_apply_url": bool(url),
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
                workflow_state={
                    "scrape_source": scrape_source,
                    "has_apply_url": bool(url),
                },
            )
        )

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def _find_by_url(self, user_id: UUID, url: str) -> Optional[DBJob]:
        result = await self.db.execute(
            select(DBJob).where(DBJob.user_id == user_id, DBJob.url == url)
        )
        return result.scalars().first()

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
