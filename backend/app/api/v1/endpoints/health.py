from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.infrastructure.db.session import get_db
from app.core.logger import logger

router = APIRouter()

@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint that verifies API and DB connectivity.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "failed"
        
    return {
        "status": "ok",
        "database": db_status
    }
