from pydantic import BaseModel, Field
from typing import List, Dict, Any
import asyncio

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry
from app.infrastructure.llm.client import structured_generate

class OptimizedResume(BaseModel):
    summary: str = Field(..., description="A newly tailored professional summary targeting the specific role")
    tailored_bullets: List[str] = Field(..., description="Top 5 most relevant experience bullets, re-written to include missing keywords where factually accurate")
    added_keywords: List[str] = Field(..., description="Keywords successfully woven into the resume")

class ResumeOptimizerAgent(OSAgent):
    name = "resume_optimizer"
    description = "Rewrites resume bullet points to naturally incorporate missing ATS keywords."
    capabilities = ["write"]

    def _mock(self, missing_skills: List[str]) -> OptimizedResume:
        skills = missing_skills or ["FastAPI", "Docker", "AWS"]
        return OptimizedResume(
            summary="Senior Backend Engineer with 5+ years experience building highly scalable microservices using Python, FastAPI, Docker, and AWS.",
            tailored_bullets=[
                "Architected and deployed scalable REST APIs using FastAPI and Docker, reducing latency by 40%.",
                "Integrated PostgreSQL databases with SQLAlchemy for robust data persistence.",
                "Deployed containerized applications to AWS ECS ensuring 99.9% uptime.",
            ],
            added_keywords=skills[:5],
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        base_resume = state.get("resume_json", "{}")
        missing_skills = state.get("ats_score", {}).get("missing_skills", [])
        job_details = state.get("job_description", "")
        system_prompt = prompt_registry.get_prompt(self.name)

        await asyncio.sleep(0.3)
        result = await structured_generate(
            OptimizedResume,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Base Resume:\n{base_resume}\n\nMissing ATS Skills:\n{', '.join(missing_skills)}\n\nJob Details:\n{job_details}"},
            ],
            fallback=lambda: self._mock(missing_skills),
        )
        return {"optimized_resume": result.model_dump()}

agent_registry.register(ResumeOptimizerAgent())
