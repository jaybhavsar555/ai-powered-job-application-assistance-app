import os
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry

class OptimizedResume(BaseModel):
    summary: str = Field(..., description="A newly tailored professional summary targeting the specific role")
    tailored_bullets: List[str] = Field(..., description="Top 5 most relevant experience bullets, re-written to include missing keywords where factually accurate")
    added_keywords: List[str] = Field(..., description="Keywords successfully woven into the resume")

class ResumeOptimizerAgent(OSAgent):
    name = "resume_optimizer"
    description = "Rewrites resume bullet points to naturally incorporate missing ATS keywords."
    capabilities = ["write"]

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = instructor.from_openai(AsyncOpenAI(api_key=self.api_key))
        else:
            self.client = None

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        base_resume = state.get("resume_json", "{}")
        missing_skills = state.get("ats_score", {}).get("missing_skills", [])
        job_details = state.get("job_description", "")
        
        system_prompt = prompt_registry.get_prompt(self.name)

        if not self.client:
            # Fallback mock for local dev without API Key
            import asyncio
            await asyncio.sleep(2.5)
            result = OptimizedResume(
                summary="Senior Backend Engineer with 5+ years experience building highly scalable microservices using Python, FastAPI, Docker, and AWS.",
                tailored_bullets=[
                    "Architected and deployed scalable REST APIs using FastAPI and Docker, reducing latency by 40%.",
                    "Integrated PostgreSQL databases with SQLAlchemy for robust data persistence.",
                    "Deployed containerized applications to AWS ECS ensuring 99.9% uptime."
                ],
                added_keywords=["FastAPI", "Docker", "AWS"]
            )
            return {"optimized_resume": result.model_dump()}
            
        result = await self.client.chat.completions.create(
            model="gpt-4o",
            response_model=OptimizedResume,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Base Resume:\n{base_resume}\n\nMissing ATS Skills:\n{', '.join(missing_skills)}\n\nJob Details:\n{job_details}"}
            ]
        )
        return {"optimized_resume": result.model_dump()}

# Register the agent
agent_registry.register(ResumeOptimizerAgent())
