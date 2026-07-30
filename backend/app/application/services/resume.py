from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List
from fastapi import HTTPException
from app.infrastructure.db.models import DBResume
from app.schemas.resume import ResumeCreate, ResumeUpdate

class ResumeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, user_id: UUID, data: ResumeCreate) -> DBResume:
        resume = DBResume(user_id=user_id, name=data.name, content=data.content)
        self.db.add(resume)
        await self.db.commit()
        await self.db.refresh(resume)
        return resume

    async def get_by_id(self, user_id: UUID, resume_id: UUID) -> DBResume:
        result = await self.db.execute(
            select(DBResume).where(DBResume.id == resume_id, DBResume.user_id == user_id)
        )
        resume = result.scalars().first()
        if not resume:
            raise HTTPException(status_code=404, detail="Resume not found")
        return resume

    async def list_by_user(self, user_id: UUID) -> List[DBResume]:
        result = await self.db.execute(
            select(DBResume).where(DBResume.user_id == user_id).order_by(DBResume.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, user_id: UUID, resume_id: UUID, data: ResumeUpdate) -> DBResume:
        resume = await self.get_by_id(user_id, resume_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(resume, key, value)
        await self.db.commit()
        await self.db.refresh(resume)
        return resume

    async def delete(self, user_id: UUID, resume_id: UUID) -> None:
        resume = await self.get_by_id(user_id, resume_id)
        await self.db.delete(resume)
        await self.db.commit()
