import os
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import Dict, Any

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry

class CoverLetter(BaseModel):
    content: str = Field(..., description="The full, professional cover letter text, properly formatted with paragraphs")
    hooks_used: list[str] = Field(..., description="The specific pain points or company research used as hooks in the introduction")

class CoverLetterAgent(OSAgent):
    name = "cover_letter_agent"
    description = "Generates highly personalized cover letters using the candidate's resume, job details, and company research."
    capabilities = ["write"]

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = instructor.from_openai(AsyncOpenAI(api_key=self.api_key))
        else:
            self.client = None

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        optimized_resume = state.get("optimized_resume", "{}")
        job_details = state.get("job_description", "")
        company_research = state.get("company_research", "No research found.")
        
        system_prompt = prompt_registry.get_prompt(self.name)

        if not self.client:
            # Fallback mock for local dev without API Key
            import asyncio
            await asyncio.sleep(3)
            result = CoverLetter(
                content="Dear Hiring Manager,\n\nI am thrilled to apply for this position. Given your recent Series B funding and focus on scaling Kubernetes, my background in deploying highly available microservices makes me an ideal fit.\n\nSincerely,\nThe Candidate",
                hooks_used=["Series B funding", "Kubernetes scaling"]
            )
            return {"cover_letter": result.model_dump()}
            
        result = await self.client.chat.completions.create(
            model="gpt-4o",
            response_model=CoverLetter,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Resume:\n{optimized_resume}\n\nJob Details:\n{job_details}\n\nCompany Research:\n{company_research}"}
            ]
        )
        return {"cover_letter": result.model_dump()}

# Register the agent
agent_registry.register(CoverLetterAgent())
