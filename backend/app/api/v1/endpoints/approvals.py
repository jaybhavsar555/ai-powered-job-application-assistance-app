from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.infrastructure.db.models import DBJob
from app.schemas.approval import (
    ApprovalDecisionRequest, 
    ApprovalDecisionResponse,
    ApprovalReevaluateRequest,
    ApprovalReevaluateResponse
)
from app.application.services.approval import ApprovalService
from app.application.agents.ats_analyzer import ATSAnalyzerAgent
import json

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

@router.post("/reevaluate", response_model=ApprovalReevaluateResponse)
async def reevaluate_approval(
    data: ApprovalReevaluateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Re-evaluate ATS score for a manually edited resume.
    """
    job_result = await db.execute(
        select(DBJob).where(DBJob.id == data.job_id, DBJob.user_id == current_user.id)
    )
    job = job_result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resume_text = json.dumps(data.tailored_resume)
    
    agent = ATSAnalyzerAgent()
    result = await agent.run({
        "resume_json": resume_text,
        "job_description": job.description_raw
    })
    
    ats_data = result.get("ats_score", {})
    return ApprovalReevaluateResponse(
        ats_score=ats_data.get("score", 0),
        evidence=f"Re-evaluated match score: {ats_data.get('score', 0)}/100. " + ats_data.get("recommendation", "")
    )
