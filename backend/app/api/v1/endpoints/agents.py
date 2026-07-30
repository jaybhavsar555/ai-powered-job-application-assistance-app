from fastapi import APIRouter, Depends, HTTPException
from typing import List

import app.application.agents  # noqa: F401 — register agents
from app.api.dependencies import get_current_user
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry
from app.domain.models import User
from app.schemas.agent import AgentInfo, AgentPromptUpdate, AgentPromptResponse

router = APIRouter()

# Canvas label helpers + human gate (not an OSAgent)
_LABELS = {
    "job_intake_agent": "Job Intake Agent",
    "company_research_agent": "Company Research Agent",
    "ats_analyzer": "ATS Analyzer",
    "resume_optimizer": "Resume Optimizer",
    "cover_letter_agent": "Cover Letter Agent",
    "human_approval": "Human Approval",
}

_HUMAN = AgentInfo(
    name="human_approval",
    label="Human Approval",
    description=(
        "Human-in-the-loop gate. After the cover letter agent finishes, drafts land on "
        "/approvals for Accept/Reject. Approving persists CoverLetter / ResumeVersion "
        "and can move the application stage to Ready."
    ),
    capabilities=["ui", "db"],
    system_prompt=None,
    configurable=False,
    role="human",
)


def _to_info(name: str, agent) -> AgentInfo:
    return AgentInfo(
        name=name,
        label=_LABELS.get(name, name.replace("_", " ").title()),
        description=getattr(agent, "description", "") or "",
        capabilities=list(getattr(agent, "capabilities", []) or []),
        system_prompt=prompt_registry.get_prompt(name),
        configurable=True,
        role="agent",
    )


@router.get("/", response_model=List[AgentInfo])
async def list_agents(current_user: User = Depends(get_current_user)):
    """Dev catalog of registered agents + Human Approval gate."""
    items = [_to_info(name, agent) for name, agent in agent_registry._agents.items()]
    items.sort(key=lambda a: a.name)
    items.append(_HUMAN)
    return items


@router.get("/{agent_name}", response_model=AgentInfo)
async def get_agent(agent_name: str, current_user: User = Depends(get_current_user)):
    if agent_name == "human_approval":
        return _HUMAN
    try:
        agent = agent_registry.get_agent(agent_name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return _to_info(agent_name, agent)


@router.put("/{agent_name}/prompt", response_model=AgentPromptResponse)
async def update_agent_prompt(
    agent_name: str,
    data: AgentPromptUpdate,
    current_user: User = Depends(get_current_user),
):
    """Update system prompt (in-memory + optional YAML persist) for local/dev tuning."""
    if agent_name == "human_approval":
        raise HTTPException(status_code=400, detail="Human Approval has no LLM prompt")
    try:
        agent_registry.get_agent(agent_name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    try:
        saved = prompt_registry.set_prompt(
            agent_name, data.system_prompt, persist=data.persist
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return AgentPromptResponse(
        name=agent_name,
        system_prompt=saved,
        persisted=data.persist,
    )
