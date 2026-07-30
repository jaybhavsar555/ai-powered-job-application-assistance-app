from typing import Dict, Any
import asyncio
from app.schemas.job import NormalizedJob

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry
from app.infrastructure.llm.client import structured_generate

class JobIntakeAgent(OSAgent):
    name = "job_intake_agent"
    description = "Extracts structured job requirements from raw text."
    capabilities = ["web"]

    def _mock(self, title: str, company: str) -> NormalizedJob:
        return NormalizedJob(
            role_title=title or "Software Engineer",
            company_name=company or "Unknown Company",
            required_skills=["Python", "FastAPI", "PostgreSQL"],
            nice_to_have_skills=["Docker", "AWS", "LangGraph"],
            years_of_experience=3,
            responsibilities=["Develop backend services", "Write unit tests", "Orchestrate AI agents"],
            benefits=["Health insurance", "Remote work", "401k"],
        )

    async def extract_and_normalize(
        self,
        raw_description: str,
        title: str = "",
        company: str = "",
    ) -> NormalizedJob:
        system_prompt = prompt_registry.get_prompt(self.name)
        # Keep prompt small — long JDs make CPU Ollama crawl
        raw = (raw_description or "")[:3500]
        await asyncio.sleep(0.05)
        return await structured_generate(
            NormalizedJob,
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Title: {title}\nCompany: {company}\n"
                        f"Description:\n{raw}"
                    ),
                },
            ],
            fallback=lambda: self._mock(title, company),
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        result = await self.extract_and_normalize(
            raw_description=state.get("job_description_raw", ""),
            title=state.get("title", ""),
            company=state.get("company", ""),
        )
        return {"normalized_job": result.model_dump()}

agent_registry.register(JobIntakeAgent())
