import logging
from typing import Any, Dict, List
from pydantic import BaseModel, Field
from textwrap import dedent

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.infrastructure.llm.client import structured_generate

logger = logging.getLogger(__name__)


class TechnicalDrill(BaseModel):
    topic: str = Field(description="The technical concept or tool.")
    question: str = Field(description="A likely technical interview question based on the JD.")
    suggested_answer: str = Field(description="A brief guide on how to answer it.")


class BehavioralDrill(BaseModel):
    behavioral_theme: str = Field(
        description="e.g., Conflict resolution, Ownership, Architecture."
    )
    question: str = Field(description="A likely behavioral question.")
    star_mapping: str = Field(
        description="Specific project or experience from the resume to use."
    )


class PitchIdea(BaseModel):
    title: str = Field(description="Short title for the pitch.")
    description: str = Field(
        description="Product or architectural suggestion to stand out."
    )


class InterviewPrepReport(BaseModel):
    company_dossier: str = Field(
        description="Cheat sheet about culture, mission, and current focus."
    )
    pitch_ideas: List[PitchIdea] = Field(description="2-3 pitch ideas.")
    technical_drills: List[TechnicalDrill] = Field(
        description="3-5 targeted technical questions."
    )
    behavioral_drills: List[BehavioralDrill] = Field(
        description="3-5 behavioral questions mapped to resume experiences."
    )


class InterviewPrepAgent(OSAgent):
    """Personalized interview prep from JD + company research + resume."""

    name = "interview_prep_agent"
    description = "Builds technical/behavioral drills and pitch ideas for interviews."
    capabilities = ["write"]

    def __init__(self) -> None:
        self.system_prompt = dedent(
            """
            You are an executive career coach and technical interview preparer.
            Produce a strategic interview prep guide as structured JSON.
            Map behavioral answers to real resume projects; drill JD skill gaps.
            """
        ).strip()

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        job_details = state.get("job_details") or state.get("job_description") or {}
        company_research = state.get("company_research") or {}
        tailored_resume = state.get("tailored_resume") or state.get("optimized_resume") or {}
        if not tailored_resume:
            tailored_resume = {"raw": state.get("resume_json", "")}

        def fallback() -> InterviewPrepReport:
            return InterviewPrepReport(
                company_dossier="Mock dossier — LLM unavailable.",
                pitch_ideas=[],
                technical_drills=[],
                behavioral_drills=[],
            )

        report = await structured_generate(
            InterviewPrepReport,
            [
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"JOB:\n{job_details}\n\n"
                        f"COMPANY:\n{company_research}\n\n"
                        f"RESUME:\n{tailored_resume}\n\n"
                        "Generate the interview prep report."
                    ),
                },
            ],
            fallback=fallback,
            max_tokens=1200,
        )
        return {"interview_prep": report.model_dump()}


agent_registry.register(InterviewPrepAgent())
