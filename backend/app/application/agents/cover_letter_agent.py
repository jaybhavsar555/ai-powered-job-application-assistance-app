from pydantic import BaseModel, Field
from typing import Dict, Any
import asyncio

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry
from app.infrastructure.llm.client import structured_generate

class CoverLetter(BaseModel):
    content: str = Field(..., description="The full, professional cover letter text, properly formatted with paragraphs")
    hooks_used: list[str] = Field(..., description="The specific pain points or company research used as hooks in the introduction")

class CoverLetterAgent(OSAgent):
    name = "cover_letter_agent"
    description = "Generates highly personalized cover letters using the candidate's resume, job details, and company research."
    capabilities = ["write"]

    def _mock(self) -> CoverLetter:
        return CoverLetter(
            content="Dear Hiring Manager,\n\nI am thrilled to apply for this position. Given your recent Series B funding and focus on scaling Kubernetes, my background in deploying highly available microservices makes me an ideal fit.\n\nSincerely,\nThe Candidate",
            hooks_used=["Series B funding", "Kubernetes scaling"],
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        optimized_resume = state.get("optimized_resume", "{}")
        job_details = state.get("job_description", "")
        company_research = state.get("company_research", "No research found.")
        system_prompt = prompt_registry.get_prompt(self.name)

        await asyncio.sleep(0.3)
        result = await structured_generate(
            CoverLetter,
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Resume:\n{optimized_resume}\n\nJob Details:\n{job_details}\n\nCompany Research:\n{company_research}"},
            ],
            fallback=self._mock,
        )
        return {"cover_letter": result.model_dump()}

agent_registry.register(CoverLetterAgent())
