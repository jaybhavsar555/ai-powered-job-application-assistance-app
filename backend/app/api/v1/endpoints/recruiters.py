from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime

from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.infrastructure.db.models import DBRecruiter, DBCompany, DBJob

router = APIRouter()


class RecruiterOut(BaseModel):
    id: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    company_id: UUID
    company_name: Optional[str] = None
    name: str
    linkedin_url: Optional[str] = None
    email: Optional[str] = None


@router.get("", response_model=List[RecruiterOut])
@router.get("/", response_model=List[RecruiterOut], include_in_schema=False)
async def list_recruiters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recruiters for companies tied to the current user's jobs."""
    stmt = (
        select(DBRecruiter, DBCompany)
        .join(DBCompany, DBRecruiter.company_id == DBCompany.id)
        .join(DBJob, DBJob.company_id == DBCompany.id)
        .where(DBJob.user_id == current_user.id)
        .order_by(DBRecruiter.name)
    )
    result = await db.execute(stmt)
    rows = result.all()

    seen: set[UUID] = set()
    recruiters: List[RecruiterOut] = []
    for r, company in rows:
        if r.id in seen:
            continue
        seen.add(r.id)
        recruiters.append(
            RecruiterOut(
                id=r.id,
                created_at=r.created_at,
                updated_at=r.updated_at,
                company_id=r.company_id,
                company_name=company.name if company else None,
                name=r.name,
                linkedin_url=r.linkedin_url,
                email=r.email,
            )
        )
    return recruiters
