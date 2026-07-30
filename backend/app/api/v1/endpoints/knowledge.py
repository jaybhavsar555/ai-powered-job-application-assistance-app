from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.schemas.knowledge import (
    WikiEntityResponse,
    WikiEntityCreate,
    WikiEntitySearchRequest,
    WikiEntitySearchHit,
    ReindexResponse,
    SeedJobPortalsResponse,
)
from app.application.services.knowledge import KnowledgeBaseService

router = APIRouter()

@router.get("/me", response_model=List[WikiEntityResponse])
async def get_my_knowledge_base(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve the current user's knowledge graph (wiki entities).
    """
    service = KnowledgeBaseService(db)
    return await service.get_by_user_id(current_user.id)

@router.post("/me", response_model=WikiEntityResponse)
async def create_wiki_entity(
    data: WikiEntityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create a wiki entity and index it into Qdrant for semantic retrieval.
    """
    service = KnowledgeBaseService(db)
    return await service.create(current_user.id, data)

@router.post("/me/search", response_model=List[WikiEntitySearchHit])
async def search_knowledge_base(
    data: WikiEntitySearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantic search over the user's long-term memory (Qdrant + embeddings).
    """
    service = KnowledgeBaseService(db)
    return await service.semantic_search(
        current_user.id,
        query=data.query,
        limit=data.limit,
        entity_type=data.entity_type,
    )

@router.get("/me/search", response_model=List[WikiEntitySearchHit])
async def search_knowledge_base_get(
    q: str = Query(..., min_length=1),
    limit: int = Query(8, ge=1, le=50),
    entity_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """GET variant of semantic search for simple clients."""
    service = KnowledgeBaseService(db)
    return await service.semantic_search(
        current_user.id,
        query=q,
        limit=limit,
        entity_type=entity_type,
    )

@router.post("/me/reindex", response_model=ReindexResponse)
async def reindex_knowledge_base(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Re-embed and upsert all of the user's wiki entities into Qdrant."""
    service = KnowledgeBaseService(db)
    indexed = await service.reindex_all(current_user.id)
    return ReindexResponse(indexed=indexed)


@router.post("/me/seed-job-portals", response_model=SeedJobPortalsResponse)
async def seed_job_portals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Idempotently seed curated job boards (Instahyre, Wellfound, YC Jobs, …)
    as `job_portal` wiki entities for browsing + later ingest.
    """
    service = KnowledgeBaseService(db)
    result = await service.seed_job_portals(current_user.id)
    return SeedJobPortalsResponse(**result)
