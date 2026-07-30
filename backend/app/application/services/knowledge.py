from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from app.infrastructure.db.models import DBWikiEntity
from app.schemas.knowledge import WikiEntityCreate, WikiEntityUpdate
from typing import List

class KnowledgeBaseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: UUID) -> List[DBWikiEntity]:
        result = await self.db.execute(
            select(DBWikiEntity).where(DBWikiEntity.user_id == user_id)
        )
        return list(result.scalars().all())

    async def create(self, user_id: UUID, data: WikiEntityCreate) -> DBWikiEntity:
        entity = DBWikiEntity(
            user_id=user_id,
            entity_type=data.entity_type,
            title=data.title,
            content=data.content,
            vector_id=data.vector_id
        )
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity
