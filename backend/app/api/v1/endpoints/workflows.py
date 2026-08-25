from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from uuid import UUID
from typing import Any, Dict, Optional
from jose import jwt, JWTError  # type: ignore
import logging

from app.core.config import get_settings
from app.domain.models import User
from app.application.services.workflow import WorkflowService
from app.api.dependencies import get_current_user, get_db
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
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

class AnalyzeJDSkillsRequest(BaseModel):
    job_description: str
    job_url: Optional[str] = None
    base_resume: str
    # Iterative tailor: score the already-tailored text instead of the library file
    resume_text: Optional[str] = None

@router.post("/analyze-jd-skills")
async def analyze_jd_skills(
    request: AnalyzeJDSkillsRequest,
    current_user: User = Depends(get_current_user)
):
    from app.application.services.ats_service import ATSService
    from app.infrastructure.resume_library import extract_text
    from app.infrastructure.scraping import scrape_job_page
    from pathlib import Path

    cfg = get_settings()
    source_dir = Path(cfg.RESUME_SOURCE_DIR)

    if request.resume_text and request.resume_text.strip():
        resume_text = request.resume_text.strip()
    else:
        file_path = source_dir / request.base_resume

        if not file_path.exists():
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Resume file not found: {request.base_resume}. "
                    "Pick a resume from the Tailor dropdown (files under data/resumes)."
                ),
            )

        resume_text = extract_text(file_path)
        if not (resume_text or "").strip():
            raise HTTPException(
                status_code=422,
                detail=f"Could not extract text from resume: {request.base_resume}",
            )

    job_text = (request.job_description or "").strip()
    scrape_source = None
    scrape_warning = None

    if request.job_url:
        scraped = await scrape_job_page(request.job_url)
        if scraped.source == "mock":
            # Scraping failed — mock body is generic and will hallucinate results.
            # Only fall back to it if the user didn't provide a manual JD either.
            if job_text:
                scrape_warning = (
                    f"Could not scrape the URL ({scraped.error or 'page blocked or JS-heavy'}). "
                    "Analysis is based on your pasted job description only."
                )
                scrape_source = "manual_jd_only"
                # job_text already set from request.job_description; don't prepend mock body
            else:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Could not scrape that URL (the page may be blocked or require a login). "
                        "Please paste the job description text manually and try again."
                    ),
                )
        else:
            # Real scraped content — prepend it to any manual JD text
            scrape_source = scraped.source
            job_text = scraped.text + ("\n" + job_text if job_text else "")

    if not job_text:
        raise HTTPException(
            status_code=422,
            detail="Please provide a job description (paste text or a scrapable URL)."
        )

    ats_service = ATSService()
    try:
        unified = await ats_service.analyze(resume_text, job_text[:12000])
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {type(exc).__name__}: {exc}",
        ) from exc
    skill_gap = ats_service.to_skill_gap_payload(unified)
    analysis_mode = unified.analysis_mode
    warning = scrape_warning
    if analysis_mode == "heuristic":
        heuristic_note = (
            "AI scoring was busy/unavailable — used a fast keyword match instead. "
            "You can still approve gaps and tailor; re-run Analyze later for a full LLM score."
        )
        warning = f"{warning} {heuristic_note}".strip() if warning else heuristic_note
    return {
        "status": "ok",
        "skill_gap": skill_gap,
        "match_score": skill_gap.get("match_score", 0),
        "rationale": skill_gap.get("rationale", ""),
        "skill_impacts": skill_gap.get("skill_impacts", []),
        "present_skills": skill_gap.get("present_skills", []),
        "nice_to_have_missing": skill_gap.get("nice_to_have_missing", []),
        "qualifications_match": skill_gap.get("qualifications_match", ""),
        "scrape_source": scrape_source,
        "scrape_warning": warning,
        "analysis_mode": analysis_mode,
        "llm_error": unified.llm_error,
        "unified_ats": unified.to_api_payload(),
    }

class TailorResumeRequest(BaseModel):
    job_description: str
    job_url: Optional[str] = None
    base_resume: str
    approved_skills: Optional[list[str]] = None
    # Iterative mode: pass the text of the already-tailored resume as the new base
    current_tailored_text: Optional[str] = None
    before_ats_score: Optional[int] = None

@router.post("/tailor-resume")
async def tailor_resume_manual(
    request: TailorResumeRequest,
    current_user: User = Depends(get_current_user)
):
    from app.application.agents.resume_optimizer import ResumeOptimizerAgent
    from app.application.agents.skill_gap_agent import heuristic_skill_gap
    from app.application.services.ats_service import ATSService
    from app.infrastructure.resume_library import extract_text
    from app.infrastructure.scraping import scrape_job_page
    from pathlib import Path

    cfg = get_settings()
    source_dir = Path(cfg.RESUME_SOURCE_DIR)
    file_path = source_dir / request.base_resume

    if request.current_tailored_text:
        resume_text = request.current_tailored_text
    else:
        if not file_path.exists():
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Resume file not found: {request.base_resume}. "
                    "Pick a resume from the Tailor dropdown."
                ),
            )
        resume_text = extract_text(file_path)
        if not (resume_text or "").strip():
            raise HTTPException(
                status_code=422,
                detail=f"Could not extract text from resume: {request.base_resume}",
            )

    job_text = (request.job_description or "").strip()
    scrape_warning = None
    if request.job_url:
        scraped = await scrape_job_page(request.job_url)
        if scraped.source == "mock":
            if job_text:
                scrape_warning = (
                    f"Could not scrape the URL ({scraped.error or 'blocked'}). "
                    "Tailoring uses your pasted JD only."
                )
            else:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "Could not scrape that URL. Paste the job description "
                        "text and try again."
                    ),
                )
        elif scraped.text:
            job_text = scraped.text + ("\n" + job_text if job_text else "")

    if not job_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Provide a job description (paste text or a scrapable URL).",
        )

    missing = request.approved_skills
    if missing is None:
        # Derive gaps from keyword heuristic when user skipped analyze step
        gap = heuristic_skill_gap(resume_text, job_text)
        missing = gap.missing_skills

    agent = ResumeOptimizerAgent()
    try:
        opt = await agent.run(
            {
                "resume_json": resume_text[:12000],
                "ats_score": {"missing_skills": missing or []},
                "job_description": job_text[:12000],
            }
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    optimized = opt.get("optimized_resume", {})

    tailored_text = "\n".join(
        [
            optimized.get("summary", ""),
            *optimized.get("tailored_bullets", []),
            *optimized.get("added_keywords", []),
        ]
    )
    ats_service = ATSService()
    after_unified = await ats_service.analyze(
        tailored_text[:6000],
        job_text[:6000],
        structured_content=optimized,
    )
    after_score = after_unified.score

    return {
        "status": "ok",
        "optimized_resume": optimized,
        "before_ats_score": request.before_ats_score,
        "after_ats_score": after_score,
        "scrape_warning": scrape_warning,
        "analysis_mode": after_unified.analysis_mode,
        "unified_ats": after_unified.to_api_payload(),
    }


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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.application.agents.job_discovery_agent import JobDiscoveryAgent
    from app.application.services.knowledge import KnowledgeBaseService

    try:
        knowledge = KnowledgeBaseService(db)
        # Ensure Vault has the curated job_portal KBs before searching them
        try:
            await knowledge.seed_job_portals(current_user.id)
        except Exception as seed_exc:
            logger.warning("Vault job_portal seed skipped: %s", seed_exc)

        agent = JobDiscoveryAgent(knowledge_service=knowledge)
        jobs = await agent.discover_and_score_jobs(
            str(current_user.id), request.model_dump()
        )
        return {"status": "ok", "jobs": jobs, "source": "discovery_agent"}
    except Exception as exc:
        logger.exception("Job discovery failed")
        raise HTTPException(
            status_code=502,
            detail=(
                f"Job discovery failed: {type(exc).__name__}: {exc}. "
                "Check Vault portals / Token Harbor and retry."
            ),
        ) from exc


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
            # Prefer skills actually present in the resume over hardcoded Flutter defaults
            from app.application.agents.skill_gap_agent import _KNOWN_SKILLS

            low = all_text.lower()
            found = [s for s in _KNOWN_SKILLS if s.lower() in low][:10]
            stack = ", ".join(found) if found else "Software engineering"
            roles = []
            if any(s in low for s in ("flutter", "dart")):
                roles.append("Flutter Developer")
            if any(s in low for s in ("react", "next.js", "typescript")):
                roles.append("Frontend Engineer")
            if any(s in low for s in ("python", "fastapi", "django")):
                roles.append("Backend Engineer")
            if any(s in low for s in ("full stack", "fullstack")):
                roles.append("Full Stack Developer")
            if not roles:
                roles = ["Software Engineer"]
            return DiscoverResumeAnalysisResponse(
                targetRoles=", ".join(roles[:3]),
                techStack=stack,
                experienceLevel="Mid-Level (2-5y)",
                locationHubs=["india"] if "india" in low or "mumbai" in low or "pune" in low or "bengaluru" in low or "bangalore" in low else ["remote"],
                companyTypes=["Startups", "Mid-size"],
                isRemote=True,
                minSalary="1000000",
            )

        try:
            result = await structured_generate(
                DiscoverResumeAnalysisResponse,
                messages,
                fallback=fallback,
                max_tokens=900,
                timeout=45.0,
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
        except Exception as llm_exc:
            logging.warning("analyze-resumes LLM failed — keyword prefs: %s", llm_exc)
            payload = fallback().model_dump()
            payload["used_resumes"] = used
            payload["available_resumes"] = available
            payload["source"] = "fallback_heuristic"
            payload["note"] = (
                "AI was busy — preferences guessed from keywords in your resume. "
                f"Files: {', '.join(used)}. Edit fields before running Discovery."
            )
            return payload
    except HTTPException:
        raise
    except Exception:
        logging.exception("Error analyzing resumes")
        return {
            "targetRoles": "Software Engineer",
            "techStack": "",
            "experienceLevel": "Mid-Level (2-5y)",
            "locationHubs": ["india"],
            "companyTypes": ["Startups", "Mid-size"],
            "isRemote": True,
            "minSalary": "1000000",
            "used_resumes": [],
            "available_resumes": [],
            "source": "fallback_error",
            "note": "Analysis failed — edit preferences manually, then run Discovery.",
        }


class ChatUpdateRequest(BaseModel):
    chat_message: str
    base_resume: Optional[str] = None

@router.post("/chat-update")
async def chat_update_profile(
    request: ChatUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.application.agents.profile_updater_agent import ProfileUpdaterAgent
    from app.infrastructure.resume_library import extract_text, list_resume_files
    from app.application.services.screening_qa import ScreeningQAService
    from pathlib import Path
    
    source_dir = Path(settings.RESUME_SOURCE_DIR)
    
    file_path = None
    if request.base_resume:
        file_path = source_dir / request.base_resume
    else:
        files = list_resume_files(source_dir)
        if files:
            file_path = files[0].path
            
    if not file_path or not file_path.exists():
        return {"status": "error", "message": "No base resume found to update."}
        
    resume_text = extract_text(file_path)
    
    agent = ProfileUpdaterAgent()
    result = await agent.run(
        {
            "chat_message": request.chat_message,
            "resume_text": resume_text,
        }
    )
    
    updated_resume_text = result.get("updated_resume_text", "")
    qa_updates = result.get("qa_updates", [])
    agent_reply = result.get("agent_reply", "")
    
    # 1. Overwrite the Master Resume if it was updated
    if updated_resume_text and updated_resume_text != resume_text:
        # We assume the base_resume is a txt or md file that can be rewritten.
        # If it's a PDF or DOCX, we write a corresponding .md file next to it.
        if file_path.suffix.lower() in [".txt", ".md"]:
            file_path.write_text(updated_resume_text, encoding="utf-8")
        else:
            md_path = file_path.with_suffix(".md")
            md_path.write_text(updated_resume_text, encoding="utf-8")
            
    # 2. Update QA Profile
    if qa_updates:
        qa_svc = ScreeningQAService(db)
        # For simplicity, we just create new items or you could check if they exist by question
        for qa in qa_updates:
            await qa_svc.create(
                user_id=current_user.id,
                question=qa.get("question", ""),
                answer=qa.get("answer", ""),
                tags=qa.get("tags", [])
            )
            
    return {
        "status": "ok",
        "agent_reply": agent_reply,
        "qa_updates": qa_updates
    }
