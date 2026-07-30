from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.schemas.knowledge import WikiEntityResponse, WikiEntityCreate
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
    Create a new wiki entity for the user.
    """
    service = KnowledgeBaseService(db)
    return await service.create(current_user.id, data)
