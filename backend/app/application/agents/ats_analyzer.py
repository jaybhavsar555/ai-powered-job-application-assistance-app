from pydantic import BaseModel, Field
from typing import List, Dict, Any

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry

class ATSAnalysisResult(BaseModel):
    score: int = Field(..., description="ATS fit score from 0 to 100")
    matching_skills: List[str] = Field(..., description="Skills found in both JD and Resume")
    missing_skills: List[str] = Field(..., description="Skills required by JD but missing from Resume")
    recommendation: str = Field(..., description="One sentence recommendation to improve ATS score")

class ATSAnalyzerAgent(OSAgent):
    name = "ats_analyzer"
    description = "Analyzes resumes against Job Descriptions to extract missing keywords and generate an ATS score."
    capabilities = ["web"]

    def _mock(self) -> ATSAnalysisResult:
        return ATSAnalysisResult(
            score=65,
            matching_skills=["Python", "SQL"],
            missing_skills=["FastAPI", "Docker", "AWS"],
            recommendation="Add FastAPI and Docker to recent experience bullets to bypass ATS filters.",
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        from app.application.services.ats_service import ATSService

        resume_content = state.get("resume_json", "{}")
        job_description = state.get("job_description", "")

        ats_service = ATSService()
        unified = await ats_service.analyze(str(resume_content), str(job_description))
        return {"ats_score": ats_service.to_legacy_ats_score(unified)}

agent_registry.register(ATSAnalyzerAgent())
