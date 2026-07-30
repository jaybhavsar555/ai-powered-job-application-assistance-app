from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.schemas.analytics import AnalyticsSummary
from app.application.services.analytics import AnalyticsService

router = APIRouter()

@router.get("/summary", response_model=AnalyticsSummary)
async def get_analytics_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Aggregate agent telemetry (tokens, latency, estimated cost, success rates)
    and pipeline stage counts for the current user.
    """
    service = AnalyticsService(db)
    return await service.get_summary(current_user.id)
