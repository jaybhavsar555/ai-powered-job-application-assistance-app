"""Optional marketplace agent — Skill Gap Coach."""
from typing import Any, Dict, List
import asyncio
from pydantic import BaseModel, Field

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.infrastructure.llm.client import structured_generate


class SkillGapPlan(BaseModel):
    missing_skills: List[str] = Field(default_factory=list)
    learning_plan: List[str] = Field(default_factory=list)
    quick_wins: List[str] = Field(default_factory=list)


class SkillGapCoachAgent(OSAgent):
    name = "skill_gap_coach"
    description = "Turns missing ATS skills into a concrete learning plan (marketplace plugin)."
    capabilities = ["coach", "marketplace"]

    def _mock(self, missing: List[str]) -> SkillGapPlan:
        skills = missing or ["FastAPI", "Docker"]
        return SkillGapPlan(
            missing_skills=skills,
            learning_plan=[
                f"Spend 2 focused hours on {skills[0]} docs + a tiny project.",
                "Add one quantified bullet per skill to your resume this week.",
            ],
            quick_wins=[f"Mention {s} in a recent project summary" for s in skills[:3]],
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        missing = state.get("missing_skills") or []
        if isinstance(missing, str):
            missing = [missing]
        await asyncio.sleep(0.2)
        result = await structured_generate(
            SkillGapPlan,
            [
                {
                    "role": "system",
                    "content": "You are a concise career coach. Build a practical skill-gap plan.",
                },
                {
                    "role": "user",
                    "content": f"Missing skills: {missing}\nRole context: {state.get('job_details', {})}",
                },
            ],
            fallback=lambda: self._mock(list(missing)),
        )
        return {"skill_gap_plan": result.model_dump()}


agent_registry.register(SkillGapCoachAgent())
