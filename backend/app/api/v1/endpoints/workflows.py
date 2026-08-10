from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from uuid import UUID
from typing import Any, Dict, Optional
from jose import jwt, JWTError  # type: ignore
import logging

from app.core.config import get_settings
from app.domain.models import User
from app.application.services.workflow import WorkflowService
from app.api.dependencies import get_current_user
from app.infrastructure.checkpoints import checkpointer_status
from app.workflows.graph import graph_backend

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


def _user_from_token(token: str) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        # EmailStr rejects reserved TLDs like .local — use a valid placeholder for SSE-only User
        return User(
            id=UUID(user_id),
            email="sse@example.com",
            auth_provider="local",
        )
    except HTTPException:
        raise
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token ({type(exc).__name__})",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token ({type(exc).__name__}: {exc})",
        ) from exc


@router.get("/checkpointer")
async def get_checkpointer_status(current_user: User = Depends(get_current_user)):
    """Report whether workflow checkpoints are durable (Postgres) or in-memory."""
    status_payload = checkpointer_status()
    return {
        **status_payload,
        "graph_backend": graph_backend(),
    }


@router.get("/{job_id}/stream")
async def stream_workflow_execution(
    job_id: UUID,
    token: Optional[str] = Query(
        None,
        description="JWT access token — EventSource cannot set Authorization headers",
    ),
    resume: bool = Query(False, description="Resume from LangGraph checkpoint for this job_id"),
):
    """
    Server-Sent Events (SSE) endpoint to stream LangGraph execution updates.
    Pass `?token=` from the frontend EventSource URL. Use `resume=true` to continue a thread.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token query param for SSE",
        )
    current_user = _user_from_token(token)
    service = WorkflowService()
    return StreamingResponse(
        service.stream_workflow(str(job_id), str(current_user.id), resume=resume),
        media_type="text/event-stream",
    )


@router.get("/{job_id}/checkpoint")
async def get_workflow_checkpoint(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Inspect LangGraph checkpoint / next nodes for a job thread."""
    service = WorkflowService()
    return await service.get_checkpoint(str(job_id))


from pydantic import BaseModel

class TailorResumeRequest(BaseModel):
    job_description: str
    base_resume: str

@router.post("/tailor-resume")
async def tailor_resume_manual(
    request: TailorResumeRequest,
    current_user: User = Depends(get_current_user)
):
    from app.application.agents.resume_optimizer import ResumeOptimizerAgent
    from app.infrastructure.resume_library import extract_text, missing_skills_from_job
    from pathlib import Path
    
    source_dir = Path(settings.RESUME_SOURCE_DIR)
    file_path = source_dir / request.base_resume
    
    if not file_path.exists():
        # Fallback to an empty template if none found just for mock
        resume_text = "Senior Software Engineer with 5 years of experience."
    else:
        resume_text = extract_text(file_path)
        
    missing = missing_skills_from_job([], resume_text) 
    
    agent = ResumeOptimizerAgent()
    opt = await agent.run(
        {
            "resume_json": resume_text[:12000],
            "ats_score": {"missing_skills": missing},
            "job_description": request.job_description,
        }
    )
    
    return {"status": "ok", "optimized_resume": opt.get("optimized_resume", {})}


class DiscoverRequest(BaseModel):
    targetRoles: str = ""
    minSalary: str = "0"
    locationHubs: list[str] = []
    isRemote: bool = True
    companyTypes: list[str] = []
    techStack: str = ""
    experienceLevel: str = ""

@router.post("/discover")
async def trigger_discovery(
    request: DiscoverRequest,
    current_user: User = Depends(get_current_user)
):
    from app.application.agents.job_discovery_agent import JobDiscoveryAgent
    try:
        agent = JobDiscoveryAgent()
        jobs = await agent.discover_and_score_jobs(str(current_user.id), request.model_dump())
        return {"status": "ok", "jobs": jobs, "source": "discovery_agent"}
    except Exception:
        logger.exception("Job discovery failed")
        raise HTTPException(
            status_code=502,
            detail="Job discovery failed — check LLM / Remotive / RemoteOK / Arbeitnow connectivity and try again",
        )


class DiscoverResumeAnalysisResponse(BaseModel):
    targetRoles: str
    minSalary: str
    locationHubs: list[str]
    isRemote: bool
    companyTypes: list[str]
    experienceLevel: str
    techStack: str


class AnalyzeResumesRequest(BaseModel):
    resume_name: Optional[str] = None  # specific library file; else use all / pick first


@router.post("/analyze-resumes")
async def analyze_resumes(
    data: Optional[AnalyzeResumesRequest] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Infer Discovery preferences from the resume library (RESUME_SOURCE_DIR).
    Optional resume_name limits analysis to one uploaded/library file.
    """
    from app.infrastructure.resume_library import list_resume_files, extract_text
    from app.infrastructure.llm.client import structured_generate
    from pathlib import Path

    req = data or AnalyzeResumesRequest()

    try:
        source_dir = Path(settings.RESUME_SOURCE_DIR)
        files = list_resume_files(source_dir)
        available = [f.name for f in files]

        if req.resume_name:
            # Path-safe: only basename under library
            safe = Path(req.resume_name).name
            selected = [f for f in files if f.name == safe]
            if not selected:
                raise HTTPException(
                    status_code=404,
                    detail=f"Resume not found in library: {safe}. Upload it first or pick another.",
                )
            files = selected

        if not files:
            return {
                "targetRoles": "Flutter Engineer, Full Stack Developer, AI Engineer",
                "techStack": "Flutter, Dart, FastAPI, React, Next.js, LangGraph, Python",
                "experienceLevel": "Mid-Level (3-5y)",
                "locationHubs": ["india", "europe"],
                "companyTypes": ["Startups", "Mid-size"],
                "isRemote": True,
                "minSalary": "1200000",
                "used_resumes": [],
                "available_resumes": available,
                "source": "fallback_no_library",
                "note": "No resumes in library — showing defaults. Upload a PDF/DOCX below.",
            }

        all_text = ""
        used = []
        for f in files[:5]:  # cap context
            used.append(f.name)
            all_text += f"\n--- Resume {f.name} ---\n{extract_text(f.path)[:5000]}"

        messages = [
            {
                "role": "system",
                "content": (
                    "Analyze the provided resume texts and extract a comprehensive "
                    "technical profile for the candidate."
                ),
            },
            {
                "role": "user",
                "content": f"Extract the profile from these resumes:\n{all_text[:12000]}",
            },
        ]

        def fallback():
            return DiscoverResumeAnalysisResponse(
                targetRoles="Flutter Engineer, Full Stack Developer",
                techStack="Flutter, Dart, FastAPI, React, LangGraph",
                experienceLevel="Mid-Level (3-5y)",
                locationHubs=["india"],
                companyTypes=["Startups"],
                isRemote=True,
                minSalary="1000000",
            )

        result = await structured_generate(
            DiscoverResumeAnalysisResponse,
            messages,
            fallback=fallback,
            max_tokens=1500,
        )
        payload = result.model_dump()
        payload["used_resumes"] = used
        payload["available_resumes"] = available
        payload["source"] = "library"
        payload["note"] = (
            f"Preferences inferred from: {', '.join(used)}"
            if used
            else "Analyzed resume library"
        )
        return payload
    except HTTPException:
        raise
    except Exception:
        logging.exception("Error analyzing resumes")
        return {
            "targetRoles": "Flutter Engineer, Full Stack Developer, AI Engineer",
            "techStack": "Flutter, Dart, FastAPI, React, Next.js, LangGraph, Python",
            "experienceLevel": "Mid-Level (3-5y)",
            "locationHubs": ["india", "europe"],
            "companyTypes": ["Startups", "Mid-size"],
            "isRemote": True,
            "minSalary": "1200000",
            "used_resumes": [],
            "available_resumes": [],
            "source": "fallback_error",
            "note": "Analysis failed — showing defaults. Try uploading a resume.",
        }
