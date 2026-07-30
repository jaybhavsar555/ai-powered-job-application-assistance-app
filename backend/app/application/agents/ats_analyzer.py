import os
import instructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from typing import List, Dict, Any

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.core.prompts.registry import prompt_registry

class ATSAnalysisResult(BaseModel):
    score: int = Field(..., description="ATS fit score from 0 to 100")
    matching_skills: List[str] = Field(..., description="Skills found in both JD and Resume")
    missing_skills: List[str] = Field(..., description="Skills required by JD but missing from Resume")
    recommendation: str = Field(..., description="One sentence recommendation to improve ATS score")

class ATSAnalyzerAgent(OSAgent):
    name = "ats_analyzer"
    description = "Analyzes resumes against Job Descriptions to extract missing keywords and generate an ATS score."
    capabilities = ["web"]

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = instructor.from_openai(AsyncOpenAI(api_key=self.api_key))
        else:
            self.client = None

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        resume_content = state.get("resume_json", "{}")
        job_description = state.get("job_description", "")
        
        system_prompt = prompt_registry.get_prompt(self.name)

        if not self.client:
            # Fallback mock for local dev without API Key
            import asyncio
            await asyncio.sleep(2)
            result = ATSAnalysisResult(
                score=65,
                matching_skills=["Python", "SQL"],
                missing_skills=["FastAPI", "Docker", "AWS"],
                recommendation="Add FastAPI and Docker to recent experience bullets to bypass ATS filters."
            )
            return {"ats_score": result.model_dump()}
            
        result = await self.client.chat.completions.create(
            model="gpt-4o",
            response_model=ATSAnalysisResult,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Resume:\n{resume_content}\n\nJob Description:\n{job_description}"}
            ]
        )
        return {"ats_score": result.model_dump()}

# Register the agent
agent_registry.register(ATSAnalyzerAgent())
