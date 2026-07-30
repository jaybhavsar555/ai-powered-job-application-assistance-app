import os
from typing import Optional, Dict, Any
import instructor
from openai import AsyncOpenAI
from app.schemas.job import NormalizedJob

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry

class JobIntakeAgent(OSAgent):
    name = "job_intake_agent"
    description = "Extracts structured job requirements from raw text."
    capabilities = ["web"]

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = instructor.from_openai(AsyncOpenAI(api_key=self.api_key))
        else:
            self.client = None

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        raw_description = state.get("job_description_raw", "")
        title = state.get("title", "")
        company = state.get("company", "")
        
        system_prompt = prompt_registry.get_prompt(self.name)

        if not self.client:
            # Fallback mock for local dev without API Key
            import asyncio
            await asyncio.sleep(1)
            result = NormalizedJob(
                role_title=title or "Software Engineer",
                company_name=company or "Unknown Company",
                required_skills=["Python", "FastAPI", "PostgreSQL"],
                nice_to_have_skills=["Docker", "AWS", "LangGraph"],
                years_of_experience=3,
                responsibilities=["Develop backend services", "Write unit tests", "Orchestrate AI agents"],
                benefits=["Health insurance", "Remote work", "401k"]
            )
            return {"normalized_job": result.model_dump()}
            
        result = await self.client.chat.completions.create(
            model="gpt-4o",
            response_model=NormalizedJob,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Title: {title}\nCompany: {company}\nDescription:\n{raw_description}"}
            ]
        )
        return {"normalized_job": result.model_dump()}

# Register the agent
agent_registry.register(JobIntakeAgent())
