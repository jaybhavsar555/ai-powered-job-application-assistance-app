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
    Re-evaluate ATS score for a manually edited resume (unified ATS + parser checks).
    """
    from app.application.services.ats_service import ATSService
    from app.application.services.resume_parser import structured_resume_to_text

    job_result = await db.execute(
        select(DBJob).where(DBJob.id == data.job_id, DBJob.user_id == current_user.id)
    )
    job = job_result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    resume_text = structured_resume_to_text(data.tailored_resume or {})
    ats_service = ATSService()
    unified = await ats_service.analyze(
        resume_text,
        job.description_raw or "",
        structured_content=data.tailored_resume,
    )
    evidence = (
        f"Re-evaluated match score: {unified.score}/100 "
        f"(LLM {unified.llm_score}, parser {unified.parser_score}). "
        f"{unified.recommendation}"
    )
    if unified.parser_checks.warnings:
        evidence += " Warnings: " + "; ".join(unified.parser_checks.warnings[:2])
    return ApprovalReevaluateResponse(ats_score=unified.score, evidence=evidence)
