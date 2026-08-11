from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from uuid import UUID
from app.api.dependencies import get_db, get_current_user
from app.domain.models import User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationStageUpdate,
    ApplicationResponse,
)
from pydantic import BaseModel
from app.application.services.application import ApplicationService

router = APIRouter()

@router.get("", response_model=List[ApplicationResponse])
@router.get("/", response_model=List[ApplicationResponse], include_in_schema=False)
async def list_applications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all applications for the current user (Kanban board data)."""
    service = ApplicationService(db)
    return await service.list_by_user(current_user.id)

@router.post("", response_model=ApplicationResponse)
@router.post("/", response_model=ApplicationResponse, include_in_schema=False)
async def create_application(
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an application for a tracked job (defaults to Wishlist)."""
    service = ApplicationService(db)
    return await service.create(current_user.id, data)

@router.get("/{application_id}", response_model=ApplicationResponse)
async def get_application(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single application with job summary."""
    service = ApplicationService(db)
    return await service.get_by_id(current_user.id, application_id)

@router.patch("/{application_id}/stage", response_model=ApplicationResponse)
async def update_application_stage(
    application_id: UUID,
    data: ApplicationStageUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Move an application to a new pipeline stage (Kanban drag-drop)."""
    service = ApplicationService(db)
    return await service.update_stage(current_user.id, application_id, data.stage)


@router.post("/{application_id}/interview-prep")
async def generate_interview_prep(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate interview prep dossier for an application."""
    from app.application.agents.interview_prep_agent import InterviewPrepAgent
    from sqlalchemy.future import select
    from app.infrastructure.db.models import DBApplication, DBInterviewPrep
    
    # 1. Fetch application and job details
    result = await db.execute(select(DBApplication).where(DBApplication.id == application_id))
    app_db = result.scalars().first()
    if not app_db or app_db.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Application not found")
        
    job_details = app_db.job.description_normalized if app_db.job else {}
    
    # 2. Get tailored resume (use workflow_state if available)
    tailored_resume = app_db.workflow_state.get("tailored_resume", {})
    company_research = app_db.workflow_state.get("company_research", {})
    
    # 3. Run Agent
    agent = InterviewPrepAgent()
    state = {
        "job_details": job_details,
        "company_research": company_research,
        "tailored_resume": tailored_resume
    }
    
    agent_result = await agent.run(state)
    prep_data = agent_result.get("interview_prep", {})
    
    # 4. Save to DB
    prep_result = await db.execute(select(DBInterviewPrep).where(DBInterviewPrep.application_id == application_id))
    db_prep = prep_result.scalars().first()
    
    if db_prep:
        db_prep.company_dossier = prep_data.get("company_dossier", {})
        db_prep.technical_drills = prep_data.get("technical_drills", [])
        db_prep.behavioral_drills = prep_data.get("behavioral_drills", [])
        db_prep.pitch_ideas = prep_data.get("pitch_ideas", [])
    else:
        db_prep = DBInterviewPrep(
            application_id=application_id,
            company_dossier=prep_data.get("company_dossier", {}),
            technical_drills=prep_data.get("technical_drills", []),
            behavioral_drills=prep_data.get("behavioral_drills", []),
            pitch_ideas=prep_data.get("pitch_ideas", [])
        )
        db.add(db_prep)
        
    await db.commit()
    
    return {"status": "ok", "interview_prep": prep_data}

@router.get("/{application_id}/interview-prep")
async def get_interview_prep(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch existing interview prep dossier."""
    from sqlalchemy.future import select
    from app.infrastructure.db.models import DBInterviewPrep, DBApplication
    
    app_result = await db.execute(select(DBApplication).where(DBApplication.id == application_id))
    app_db = app_result.scalars().first()
    if not app_db or app_db.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Application not found")
        
    result = await db.execute(select(DBInterviewPrep).where(DBInterviewPrep.application_id == application_id))
    db_prep = result.scalars().first()
    
    if not db_prep:
        return {"status": "not_found", "interview_prep": None}
        
    return {
        "status": "ok",
        "interview_prep": {
            "company_dossier": db_prep.company_dossier,
            "technical_drills": db_prep.technical_drills,
            "behavioral_drills": db_prep.behavioral_drills,
            "pitch_ideas": db_prep.pitch_ideas
        }
    }


class MockInterviewMessage(BaseModel):
    role: str
    content: str

class MockInterviewRequest(BaseModel):
    messages: List[MockInterviewMessage]

@router.post("/{application_id}/mock-interview")
async def mock_interview_chat(
    application_id: UUID,
    request: MockInterviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Conversational endpoint for the mock interview simulator."""
    from sqlalchemy.future import select
    from app.infrastructure.db.models import DBApplication
    from app.infrastructure.llm.client import text_generate
    import json
    
    app_result = await db.execute(select(DBApplication).where(DBApplication.id == application_id))
    app_db = app_result.scalars().first()
    if not app_db or app_db.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Application not found")
        
    job_details = app_db.job.description_normalized if app_db.job else {}
    company_name = job_details.get("company_name", "the company")
    role_title = job_details.get("role_title", "the role")
    
    system_prompt = (
        f"You are a strict but fair Hiring Manager at {company_name} interviewing a candidate for the {role_title} role.\n"
        "Ask one question at a time. Evaluate their previous answer briefly before asking the next question.\n"
        "Keep it conversational, professional, and focus on technical and behavioral fit."
    )
    
    # Convert incoming messages to LLM format
    llm_messages = [{"role": "system", "content": system_prompt}]
    for m in request.messages:
        llm_messages.append({"role": m.role, "content": m.content})
        
    try:
        reply = await text_generate(llm_messages)
    except Exception as e:
        reply = "I'm having trouble connecting to my audio interface. Could we reschedule? (Error connecting to LLM)"
        
    return {"status": "ok", "reply": reply}
