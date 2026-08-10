from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.application.services.screening_qa import ScreeningQAService

router = APIRouter()


class ScreeningQACreate(BaseModel):
    question: str = Field(..., min_length=2)
    answer: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)


class ScreeningQAUpdate(BaseModel):
    question: Optional[str] = None
    answer: Optional[str] = None
    tags: Optional[List[str]] = None


@router.get("")
@router.get("/", include_in_schema=False)
async def list_screening_qa(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List saved screening questions/answers for autofill."""
    return await ScreeningQAService(db).list(current_user.id)


@router.post("")
@router.post("/", include_in_schema=False)
async def create_screening_qa(
    data: ScreeningQACreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ScreeningQAService(db).create(
        current_user.id, data.question, data.answer, data.tags
    )


@router.get("/match")
async def match_screening_qa(
    q: str = Query(..., min_length=2),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Match a form question to saved answers (used by Chrome extension)."""
    return await ScreeningQAService(db).match(current_user.id, q, limit=limit)


@router.post("/seed-defaults")
@router.post("/seed-defaults/", include_in_schema=False)
async def seed_screening_qa_defaults(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Seed common ATS screening Q&A so daily autofill is not empty."""
    return await ScreeningQAService(db).seed_defaults(current_user.id)


@router.patch("/{qa_id}")
async def update_screening_qa(
    qa_id: UUID,
    data: ScreeningQAUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await ScreeningQAService(db).update(
        current_user.id,
        qa_id,
        question=data.question,
        answer=data.answer,
        tags=data.tags,
    )


@router.delete("/{qa_id}")
async def delete_screening_qa(
    qa_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await ScreeningQAService(db).delete(current_user.id, qa_id)
    return {"status": "ok"}
