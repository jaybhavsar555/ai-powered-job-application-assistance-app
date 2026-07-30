from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.schemas.approval import ApprovalDecisionRequest, ApprovalDecisionResponse
from app.application.services.approval import ApprovalService

router = APIRouter()

@router.post("/decide", response_model=ApprovalDecisionResponse)
async def decide_approval(
    data: ApprovalDecisionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Human-in-the-loop decision: approve persists CoverLetter / ResumeVersion,
    reject records the decision. Approving advances stage Wishlist/Researching → Ready.
    """
    service = ApprovalService(db)
    return await service.decide(current_user.id, data)
