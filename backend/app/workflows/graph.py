from typing import Optional
from langgraph.graph import StateGraph, END
from sqlalchemy.future import select
from uuid import UUID
import json

from app.workflows.state import AgentState
from app.application.agents.registry import agent_registry
import app.application.agents  # noqa: F401 — register all agents
from app.infrastructure.db.session import async_session
from app.infrastructure.db.models import DBJob
from pathlib import Path
from app.core.config import get_settings
from app.infrastructure.resume_library import detect_role_family, pick_base_resume, extract_text

_app_graph = None
_graph_backend: str = "uninitialized"


async def _load_job(job_id: str) -> Optional[DBJob]:
    try:
        uid = UUID(job_id)
    except (ValueError, TypeError):
        return None
    async with async_session() as session:
        result = await session.execute(select(DBJob).where(DBJob.id == uid))
        return result.scalars().first()


def _get_base_resume_text(job_details: dict) -> str:
    settings = get_settings()
    source = Path(settings.RESUME_SOURCE_DIR)
    
    role_title = job_details.get("role_title") or "Role"
    jd = job_details.get("description_raw") or ""
    
    role_family = detect_role_family(role_title, jd)
    base = pick_base_resume(source, role_family)
    
    if base:
        resume_text = extract_text(base.path)
        if resume_text:
            return resume_text
            
    return "Mock base resume with Python and SQL."


async def job_intake_node(state: AgentState):
    agent = agent_registry.get_agent("job_intake_agent")
    job = await _load_job(state.get("job_id", ""))

    if job:
        agent_state = {
            "job_description_raw": job.description_raw or "",
            "title": job.role_title or "",
            "company": (job.description_normalized or {}).get("company_name", ""),
        }
    else:
        agent_state = {
            "job_description_raw": "Mock raw job content from URL",
            "title": "Software Engineer",
            "company": "Tech Corp",
        }

    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    return {
        "messages": ["Extracted requirements and normalized job description."],
        "job_details": result.get("normalized_job"),
        "job_url": job.url if job else None,
    }


async def memory_retrieval_node(state: AgentState):
    from app.application.services.knowledge import KnowledgeBaseService
    user_id = state.get("user_id")
    if not user_id:
        return {"long_term_memory": []}
    
    try:
        uid = UUID(user_id)
    except Exception:
        return {"long_term_memory": []}

    job = state.get("job_details") or {}
    title = job.get("role_title") or ""
    company = job.get("company_name") or ""
    
    query = f"{title} at {company}".strip()
    if not query:
        query = "Software Engineering"
    
    try:
        async with async_session() as session:
            svc = KnowledgeBaseService(session)
            hits = await svc.semantic_search(uid, query=query, limit=5)
            memory_list = []
            for h in hits:
                memory_list.append({
                    "title": h.title,
                    "type": h.entity_type,
                    "content": h.content
                })
            
            return {
                "messages": [f"Retrieved {len(hits)} relevant memories from Vault."],
                "long_term_memory": memory_list
            }
    except Exception as e:
        print(f"Memory Retrieval Error: {e}")
        return {"long_term_memory": []}


async def company_research_node(state: AgentState):
    agent = agent_registry.get_agent("company_research_agent")
    job = state.get("job_details") or {}
    agent_state = {
        "job_details": job,
        "company": job.get("company_name", "Tech Corp"),
        "title": job.get("role_title", ""),
        "job_url": state.get("job_url"),
    }
    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    research = result.get("company_research", {})
    hooks = research.get("recent_news_hooks") or []

    try:
        from app.application.services.workflow_persistence import persist_company_research

        async with async_session() as session:
            await persist_company_research(
                session, job_id=state.get("job_id"), research=research or {}
            )
    except Exception as e:
        print(f"[persist] company_research failed: {e}")

    return {
        "messages": [
            f"Researched {research.get('company_name', 'company')}.",
            f"Hooks: {', '.join(hooks[:3])}" if hooks else "Research complete.",
        ],
        "company_research": research,
    }


async def ats_analysis_node(state: AgentState):
    agent = agent_registry.get_agent("ats_analyzer")
    job_details = state.get("job_details", {})
    job_str = json.dumps(job_details)
    base_resume = _get_base_resume_text(job_details)

    agent_state = {
        "resume_json": base_resume,
        "job_description": job_str,
    }

    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    ats_res = result.get("ats_score", {})

    try:
        from app.application.services.workflow_persistence import persist_ats_and_approval_flags

        async with async_session() as session:
            await persist_ats_and_approval_flags(
                session,
                job_id=state.get("job_id"),
                ats_score=ats_res.get("score"),
                missing_skills=ats_res.get("missing_skills") or [],
                matching_skills=ats_res.get("matching_skills") or [],
                ats_recommendation=ats_res.get("recommendation"),
            )
    except Exception as e:
        print(f"[persist] ats failed: {e}")

    return {
        "messages": [
            f"ATS Analysis completed. Score: {ats_res.get('score')}%.",
            f"Missing critical skills: {', '.join(ats_res.get('missing_skills', []))}",
        ],
        "ats_score": ats_res.get("score"),
        "missing_skills": ats_res.get("missing_skills", []),
        "matching_skills": ats_res.get("matching_skills", []),
    }


async def resume_optimization_node(state: AgentState):
    agent = agent_registry.get_agent("resume_optimizer")
    job_details = state.get("job_details", {})
    job_str = json.dumps(job_details)
    base_resume = _get_base_resume_text(job_details)

    agent_state = {
        "resume_json": base_resume,
        "ats_score": {"missing_skills": state.get("missing_skills", [])},
        "job_description": job_str,
    }

    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    opt_res = result.get("optimized_resume", {})

    try:
        from app.application.services.workflow_persistence import persist_ats_and_approval_flags

        async with async_session() as session:
            await persist_ats_and_approval_flags(
                session,
                job_id=state.get("job_id"),
                tailored_resume=opt_res or {},
            )
    except Exception as e:
        print(f"[persist] resume failed: {e}")

    return {
        "messages": [
            "Optimized resume tailored to JD.",
            f"Successfully added keywords: {', '.join(opt_res.get('added_keywords', []))}",
        ],
        "tailored_resume": opt_res,
        "resume_json": base_resume,
    }


async def hallucination_check_node(state: AgentState):
    agent = agent_registry.get_agent("hallucination_checker")
    
    agent_state = {
        "resume_json": state.get("resume_json", ""),
        "tailored_resume": state.get("tailored_resume", {}),
    }

    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    report = result.get("hallucination_report", {})
    
    msgs = ["Factual consistency check passed."]
    if report.get("has_hallucination"):
        msgs = [f"Hallucination Warning: {', '.join(report.get('hallucinated_claims', []))}"]
        
        try:
            from app.application.services.workflow_persistence import persist_ats_and_approval_flags
            async with async_session() as session:
                # Update approval flags in the database so the UI can warn the user
                await persist_ats_and_approval_flags(
                    session,
                    job_id=state.get("job_id"),
                    requires_human_approval=True,
                )
        except Exception as e:
            print(f"[persist] hallucination flag failed: {e}")

    return {
        "messages": msgs,
        "hallucination_report": report
    }


async def cover_letter_node(state: AgentState):
    agent = agent_registry.get_agent("cover_letter_agent")
    job_str = json.dumps(state.get("job_details", {}))
    resume_str = json.dumps(state.get("tailored_resume", {}))
    company_str = json.dumps(state.get("company_research", {}))

    agent_state = {
        "optimized_resume": resume_str,
        "job_description": job_str,
        "company_research": company_str,
    }

    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    cl_res = result.get("cover_letter", {})
    cover_text = cl_res.get("content")

    try:
        from app.application.services.workflow_persistence import persist_ats_and_approval_flags

        async with async_session() as session:
            await persist_ats_and_approval_flags(
                session,
                job_id=state.get("job_id"),
                cover_letter=cover_text,
                requires_human_approval=True,
            )
    except Exception as e:
        print(f"[persist] cover_letter failed: {e}")

    return {
        "messages": [
            "Generated highly personalized Cover Letter.",
            f"Hooks used: {', '.join(cl_res.get('hooks_used', []))}",
        ],
        "cover_letter": cover_text,
        "requires_human_approval": True,
    }


async def recruiter_discovery_node(state: AgentState):
    agent = agent_registry.get_agent("recruiter_discovery_agent")
    result = await agent.execute(state, application_id=state.get("job_id"))
    rd_res = result.get("recruiter_discovery", {})

    try:
        from app.application.services.workflow_persistence import persist_recruiter_discovery

        async with async_session() as session:
            await persist_recruiter_discovery(
                session, job_id=state.get("job_id"), discovery=rd_res or {}
            )
    except Exception as e:
        print(f"[persist] recruiter_discovery failed: {e}")

    return {
        "messages": [
            f"Discovered Recruiter: {rd_res.get('recruiter_name')} ({rd_res.get('recruiter_email')})"
        ],
        "recruiter_discovery": rd_res,
    }


async def outreach_draft_node(state: AgentState):
    agent = agent_registry.get_agent("outreach_draft_agent")
    result = await agent.execute(state, application_id=state.get("job_id"))
    draft_res = result.get("outreach_draft", {})

    try:
        from app.application.services.workflow_persistence import persist_outreach_draft

        async with async_session() as session:
            await persist_outreach_draft(
                session,
                job_id=state.get("job_id"),
                draft=draft_res or {},
            )
    except Exception as e:
        print(f"[persist] outreach_draft failed: {e}")

    return {
        "messages": [
            "Generated highly personalized Outreach Draft."
        ],
        "outreach_draft": draft_res,
    }


def build_graph(checkpointer=None, *, backend: str = "memory"):
    """Compile the Career OS agent graph with the given checkpointer."""
    global _app_graph, _graph_backend

    workflow = StateGraph(AgentState)

    workflow.add_node("Job Intake Agent", job_intake_node)
    workflow.add_node("Memory Retrieval Node", memory_retrieval_node)
    workflow.add_node("Company Research Agent", company_research_node)
    workflow.add_node("ATS Analyzer", ats_analysis_node)
    workflow.add_node("Resume Optimizer", resume_optimization_node)
    workflow.add_node("Hallucination Checker", hallucination_check_node)
    workflow.add_node("Cover Letter Agent", cover_letter_node)
    workflow.add_node("Recruiter Discovery Agent", recruiter_discovery_node)
    workflow.add_node("Outreach Draft Agent", outreach_draft_node)

    workflow.set_entry_point("Job Intake Agent")

    # Flow: Intake -> Memory -> (Company Research, ATS Analyzer)
    workflow.add_edge("Job Intake Agent", "Memory Retrieval Node")
    workflow.add_edge("Memory Retrieval Node", "Company Research Agent")
    workflow.add_edge("Memory Retrieval Node", "ATS Analyzer")
    
    workflow.add_edge("ATS Analyzer", "Resume Optimizer")
    workflow.add_edge("Resume Optimizer", "Hallucination Checker")
    # Cover letter waits for both hallucination check + company research (LangGraph join).
    workflow.add_edge("Hallucination Checker", "Cover Letter Agent")
    workflow.add_edge("Company Research Agent", "Cover Letter Agent")
    
    # New flow: Cover Letter -> Recruiter Discovery -> Outreach Draft -> END
    workflow.add_edge("Cover Letter Agent", "Recruiter Discovery Agent")
    workflow.add_edge("Recruiter Discovery Agent", "Outreach Draft Agent")
    workflow.add_edge("Outreach Draft Agent", END)

    if checkpointer is None:
        from langgraph.checkpoint.memory import MemorySaver

        checkpointer = MemorySaver()
        backend = "memory"

    compiled = workflow.compile(checkpointer=checkpointer)
    _app_graph = compiled
    _graph_backend = backend
    return compiled


def get_app_graph():
    """Return the compiled graph (bootstraps MemorySaver if startup has not run yet)."""
    global _app_graph
    if _app_graph is None:
        build_graph()
    return _app_graph


def graph_backend() -> str:
    return _graph_backend


# Eager compile with memory so imports/tests work before FastAPI startup
app_graph = build_graph()


def thread_config(job_id: str) -> dict:
    return {"configurable": {"thread_id": str(job_id)}}
