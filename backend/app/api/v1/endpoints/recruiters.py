from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from pydantic import BaseModel, Field
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


class RecruiterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    email: Optional[str] = Field(None, max_length=320)
    linkedin_url: Optional[str] = Field(None, max_length=500)


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


@router.patch("/{recruiter_id}", response_model=RecruiterOut)
async def update_recruiter(
    recruiter_id: UUID,
    data: RecruiterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update recruiter contact for companies linked to the current user's jobs."""
    stmt = (
        select(DBRecruiter, DBCompany)
        .join(DBCompany, DBRecruiter.company_id == DBCompany.id)
        .join(DBJob, DBJob.company_id == DBCompany.id)
        .where(DBRecruiter.id == recruiter_id, DBJob.user_id == current_user.id)
    )
    row = (await db.execute(stmt)).first()
    if not row:
        raise HTTPException(status_code=404, detail="Recruiter not found")
    recruiter, company = row

    if data.name is not None:
        recruiter.name = data.name.strip()
    if data.email is not None:
        email = data.email.strip() or None
        if email and "@" not in email:
            raise HTTPException(status_code=400, detail="Email looks invalid")
        recruiter.email = email
    if data.linkedin_url is not None:
        linkedin = data.linkedin_url.strip() or None
        recruiter.linkedin_url = linkedin

    await db.commit()
    await db.refresh(recruiter)
    return RecruiterOut(
        id=recruiter.id,
        created_at=recruiter.created_at,
        updated_at=recruiter.updated_at,
        company_id=recruiter.company_id,
        company_name=company.name if company else None,
        name=recruiter.name,
        linkedin_url=recruiter.linkedin_url,
        email=recruiter.email,
    )
