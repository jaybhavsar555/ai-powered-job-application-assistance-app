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
    return {
        "messages": [
            f"Researched {research.get('company_name', 'company')}.",
            f"Hooks: {', '.join(hooks[:3])}" if hooks else "Research complete.",
        ],
        "company_research": research,
    }


async def ats_analysis_node(state: AgentState):
    agent = agent_registry.get_agent("ats_analyzer")
    job_str = json.dumps(state.get("job_details", {}))
    base_resume = "Mock base resume with Python and SQL."

    agent_state = {
        "resume_json": base_resume,
        "job_description": job_str,
    }

    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    ats_res = result.get("ats_score", {})

    return {
        "messages": [
            f"ATS Analysis completed. Score: {ats_res.get('score')}%.",
            f"Missing critical skills: {', '.join(ats_res.get('missing_skills', []))}",
        ],
        "ats_score": ats_res.get("score"),
        "missing_skills": ats_res.get("missing_skills", []),
    }


async def resume_optimization_node(state: AgentState):
    agent = agent_registry.get_agent("resume_optimizer")
    job_str = json.dumps(state.get("job_details", {}))
    base_resume = "Mock base resume with Python and SQL."

    agent_state = {
        "resume_json": base_resume,
        "ats_score": {"missing_skills": state.get("missing_skills", [])},
        "job_description": job_str,
    }

    result = await agent.execute(agent_state, application_id=state.get("job_id"))
    opt_res = result.get("optimized_resume", {})

    return {
        "messages": [
            "Optimized resume tailored to JD.",
            f"Successfully added keywords: {', '.join(opt_res.get('added_keywords', []))}",
        ],
        "tailored_resume": opt_res,
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

    return {
        "messages": [
            "Generated highly personalized Cover Letter.",
            f"Hooks used: {', '.join(cl_res.get('hooks_used', []))}",
        ],
        "cover_letter": cl_res.get("content"),
        "requires_human_approval": True,
    }


def build_graph(checkpointer=None, *, backend: str = "memory"):
    """Compile the Career OS agent graph with the given checkpointer."""
    global _app_graph, _graph_backend

    workflow = StateGraph(AgentState)

    workflow.add_node("Job Intake Agent", job_intake_node)
    workflow.add_node("Company Research Agent", company_research_node)
    workflow.add_node("ATS Analyzer", ats_analysis_node)
    workflow.add_node("Resume Optimizer", resume_optimization_node)
    workflow.add_node("Cover Letter Agent", cover_letter_node)

    workflow.set_entry_point("Job Intake Agent")

    workflow.add_edge("Job Intake Agent", "Company Research Agent")
    workflow.add_edge("Company Research Agent", "ATS Analyzer")
    workflow.add_edge("ATS Analyzer", "Resume Optimizer")
    workflow.add_edge("Resume Optimizer", "Cover Letter Agent")
    workflow.add_edge("Cover Letter Agent", END)

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
