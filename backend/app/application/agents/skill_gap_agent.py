from pydantic import BaseModel, Field
from typing import List, Dict, Any

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.infrastructure.llm.client import structured_generate

class SkillGapAnalysis(BaseModel):
    missing_skills: List[str] = Field(..., description="List of technical or soft skills required by the JD that are completely missing from the base resume")
    match_score: int = Field(..., description="A score from 0-100 indicating how well the base resume matches the job description")
    rationale: str = Field(..., description="A short explanation of the gap analysis")

class SkillGapAgent(OSAgent):
    name = "skill_gap_agent"
    description = "Analyzes a job description against a base resume to identify missing skills without modifying the resume."
    capabilities = ["analyze"]

    def _mock(self) -> SkillGapAnalysis:
        return SkillGapAnalysis(
            missing_skills=["Kubernetes", "GraphQL", "System Design"],
            match_score=75,
            rationale="Strong match for backend engineering, but missing specific devops tooling mentioned in the JD."
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        base_resume = state.get("resume_json", "{}")
        job_details = state.get("job_description", "")
        
        system_prompt = (
            "You are an expert technical recruiter and ATS specialist. Your task is to compare a candidate's base resume "
            "against a job description. Identify critical required skills, tools, or experiences in the JD that are completely "
            "missing from the candidate's resume. Be strictly factual. Do not hallucinate."
        )

        result = await structured_generate(
            SkillGapAnalysis,
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Base Resume:\n{(base_resume or '')[:3000]}\n\n"
                        f"Job Description:\n{(job_details or '')[:3000]}"
                    ),
                },
            ],
            fallback=self._mock,
        )
        return {"skill_gap": result.model_dump()}

agent_registry.register(SkillGapAgent())
