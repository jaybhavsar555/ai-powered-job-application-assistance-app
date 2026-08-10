from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.infrastructure.db.models import DBCompany, DBJob

router = APIRouter()


class CompanyOut(BaseModel):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    name: str
    research_data: dict = Field(default_factory=dict)
    job_count: int = 0


@router.get("", response_model=List[CompanyOut])
@router.get("/", response_model=List[CompanyOut], include_in_schema=False)
async def list_companies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List companies linked to the current user's jobs."""
    stmt = (
        select(DBCompany, DBJob)
        .join(DBJob, DBJob.company_id == DBCompany.id)
        .where(DBJob.user_id == current_user.id)
        .order_by(DBCompany.name)
    )
    result = await db.execute(stmt)
    rows = result.all()

    by_id: dict[UUID, CompanyOut] = {}
    for company, _job in rows:
        existing = by_id.get(company.id)
        if existing:
            existing.job_count += 1
            continue
        by_id[company.id] = CompanyOut(
            id=company.id,
            created_at=company.created_at,
            updated_at=company.updated_at,
            name=company.name,
            research_data=company.research_data or {},
            job_count=1,
        )
    return list(by_id.values())
