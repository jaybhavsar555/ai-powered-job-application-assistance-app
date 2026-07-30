from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID
from typing import List, Optional
from app.infrastructure.db.models import DBWikiEntity
from app.schemas.knowledge import WikiEntityCreate, WikiEntitySearchHit
from app.infrastructure.memory.embeddings import embed_text, entity_to_embed_text
from app.infrastructure.memory.vector_store import get_vector_memory, new_vector_id

class KnowledgeBaseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_user_id(self, user_id: UUID) -> List[DBWikiEntity]:
        result = await self.db.execute(
            select(DBWikiEntity).where(DBWikiEntity.user_id == user_id)
            .order_by(DBWikiEntity.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_ids(self, user_id: UUID, entity_ids: List[UUID]) -> List[DBWikiEntity]:
        if not entity_ids:
            return []
        result = await self.db.execute(
            select(DBWikiEntity).where(
                DBWikiEntity.user_id == user_id,
                DBWikiEntity.id.in_(entity_ids),
            )
        )
        by_id = {e.id: e for e in result.scalars().all()}
        # Preserve search-rank order
        return [by_id[i] for i in entity_ids if i in by_id]

    async def create(self, user_id: UUID, data: WikiEntityCreate) -> DBWikiEntity:
        entity = DBWikiEntity(
            user_id=user_id,
            entity_type=data.entity_type,
            title=data.title,
            content=data.content,
            vector_id=data.vector_id,
        )
        self.db.add(entity)
        await self.db.flush()

        # Index into Qdrant for semantic retrieval
        try:
            vector_id = data.vector_id or new_vector_id()
            text = entity_to_embed_text(data.title, data.entity_type, data.content or {})
            vector = await embed_text(text)
            get_vector_memory().upsert_entity(
                vector_id=vector_id,
                user_id=user_id,
                entity_id=entity.id,
                entity_type=data.entity_type,
                title=data.title,
                vector=vector,
            )
            entity.vector_id = vector_id
        except Exception:
            # Vault create should succeed even if Qdrant is temporarily down
            pass

        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def semantic_search(
        self,
        user_id: UUID,
        query: str,
        limit: int = 8,
        entity_type: Optional[str] = None,
    ) -> List[WikiEntitySearchHit]:
        query_vector = await embed_text(query)
        hits = get_vector_memory().search(
            user_id=user_id,
            query_vector=query_vector,
            limit=limit,
            entity_type=entity_type,
        )
        if not hits:
            return []

        entity_ids: List[UUID] = []
        score_by_id = {}
        for h in hits:
            try:
                eid = UUID(str(h["entity_id"]))
            except Exception:
                continue
            entity_ids.append(eid)
            score_by_id[eid] = h["score"]

        entities = await self.get_by_ids(user_id, entity_ids)
        return [
            WikiEntitySearchHit(
                id=e.id,
                user_id=e.user_id,
                entity_type=e.entity_type,
                title=e.title,
                content=e.content or {},
                vector_id=e.vector_id,
                score=score_by_id.get(e.id, 0.0),
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in entities
        ]

    async def reindex_all(self, user_id: UUID) -> int:
        """Re-embed all entities for a user (useful after embedding model change)."""
        entities = await self.get_by_user_id(user_id)
        count = 0
        for entity in entities:
            try:
                vector_id = entity.vector_id or new_vector_id()
                text = entity_to_embed_text(
                    entity.title, entity.entity_type, entity.content or {}
                )
                vector = await embed_text(text)
                get_vector_memory().upsert_entity(
                    vector_id=vector_id,
                    user_id=user_id,
                    entity_id=entity.id,
                    entity_type=entity.entity_type,
                    title=entity.title,
                    vector=vector,
                )
                entity.vector_id = vector_id
                count += 1
            except Exception:
                continue
        await self.db.commit()
        return count

    async def seed_job_portals(self, user_id: UUID) -> dict:
        """Idempotently add curated job-board portals as wiki entities."""
        from app.core.job_portals import JOB_PORTALS

        existing = await self.get_by_user_id(user_id)
        existing_urls = set()
        for e in existing:
            if e.entity_type != "job_portal":
                continue
            content = e.content or {}
            url = content.get("url")
            if isinstance(url, str):
                existing_urls.add(url.rstrip("/").lower())

        created = 0
        skipped = 0
        for portal in JOB_PORTALS:
            url = str(portal["url"]).rstrip("/")
            key = url.lower()
            if key in existing_urls:
                skipped += 1
                continue
            await self.create(
                user_id,
                WikiEntityCreate(
                    entity_type="job_portal",
                    title=portal["title"],
                    content={
                        "url": portal["url"],
                        "region": portal.get("region", "Global"),
                        "note": f"Job posting portal — {portal['title']}. Browse openings, then paste a posting URL into Tracker → Import job.",
                        "category": "job_board",
                    },
                ),
            )
            existing_urls.add(key)
            created += 1

        roles_created = await self._seed_target_roles(user_id)
        return {
            "created": created,
            "skipped": skipped,
            "total": len(JOB_PORTALS),
            "target_roles_created": roles_created,
        }

    async def _seed_target_roles(self, user_id: UUID) -> int:
        """Idempotently add target role tags used when picking a base resume."""
        from app.core.target_roles import TARGET_ROLES

        existing = await self.get_by_user_id(user_id)
        existing_ids = {
            (e.content or {}).get("role_id")
            for e in existing
            if e.entity_type == "target_role"
        }
        created = 0
        for role in TARGET_ROLES:
            if role["id"] in existing_ids:
                continue
            await self.create(
                user_id,
                WikiEntityCreate(
                    entity_type="target_role",
                    title=role["label"],
                    content={
                        "role_id": role["id"],
                        "keywords": role["keywords"],
                        "note": "Used to pick a base resume from RESUME_SOURCE_DIR when generating an apply package.",
                    },
                ),
            )
            created += 1
        return created
