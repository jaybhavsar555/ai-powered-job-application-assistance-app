from pydantic import BaseModel, Field
from typing import List, Dict, Any, Literal

from app.application.agents.base import OSAgent
from app.application.agents.registry import agent_registry
from app.infrastructure.llm.client import structured_generate


class SkillImpact(BaseModel):
    skill: str = Field(..., description="The skill name exactly as mentioned in the JD")
    level: Literal["high", "medium", "low"] = Field(..., description="Impact level if this skill is added")
    reason: str = Field(..., description="One sentence: why this skill matters for this specific role")
    jd_mentions: int = Field(default=1, description="How many times this skill appears/is implied in the JD")


class SkillPresent(BaseModel):
    skill: str = Field(..., description="Skill from JD that IS present in the resume")
    confidence: Literal["strong", "partial"] = Field(..., description="strong = exact match; partial = implied or adjacent")
    note: str = Field(default="", description="Brief note on how it's demonstrated in the resume")


class NiceToHaveSkill(BaseModel):
    skill: str = Field(..., description="Nice-to-have skill from the JD")
    reason: str = Field(..., description="Why it's nice-to-have, not required")


class SkillGapAnalysis(BaseModel):
    # Scoring
    match_score: int = Field(..., description="Score 0-100: how well the resume matches this specific JD")
    rationale: str = Field(..., description="2-3 sentence summary of the overall match quality")

    # What's missing (required by JD, absent from resume)
    missing_skills: List[str] = Field(
        ...,
        description="Skills explicitly REQUIRED by the JD that are completely absent from the resume. Be strict — only list skills actually in the JD."
    )
    skill_impacts: List[SkillImpact] = Field(
        default_factory=list,
        description="Per-skill impact analysis for each missing required skill"
    )

    # What's already present
    present_skills: List[SkillPresent] = Field(
        default_factory=list,
        description="Skills from the JD that ARE present in the resume (gives confidence of match)"
    )

    # Nice-to-have gaps
    nice_to_have_missing: List[NiceToHaveSkill] = Field(
        default_factory=list,
        description="Skills the JD lists as 'nice to have', 'bonus', or 'preferred' that are absent from the resume"
    )

    # Qualifications check
    qualifications_match: str = Field(
        default="",
        description="Brief comment on whether the candidate meets the stated qualifications (degree, years of experience)"
    )


class SkillGapAgent(OSAgent):
    name = "skill_gap_agent"
    description = "Thorough word-by-word analysis of a resume against a job description. Identifies required missing, nice-to-have missing, and present skills."
    capabilities = ["analyze"]

    def _mock(self) -> SkillGapAnalysis:
        return SkillGapAnalysis(
            missing_skills=["State-Machine Design", "Advanced OOPs Concepts"],
            match_score=65,
            rationale="Strong Flutter/Dart foundation but missing explicit state-machine design patterns and advanced OOPs depth called out in the JD.",
            skill_impacts=[
                SkillImpact(skill="State-Machine Design", level="high", reason="Primary skillset requirement — directly listed in the JD.", jd_mentions=2),
                SkillImpact(skill="Advanced OOPs Concepts", level="high", reason="Core requirement for maintaining the server-driven agentic architecture.", jd_mentions=2),
            ],
            present_skills=[
                SkillPresent(skill="Flutter", confidence="strong", note="Explicitly listed with production experience"),
                SkillPresent(skill="Dart", confidence="strong", note="Primary language for Flutter development"),
            ],
            nice_to_have_missing=[
                NiceToHaveSkill(skill="Fintech experience", reason="JD says 'nice to have: fintech or offline-first sync' — not a hard requirement"),
            ],
            qualifications_match="Candidate meets the bachelor's degree requirement and experience level."
        )

    async def run(self, state: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
        base_resume = state.get("resume_json", "{}")
        job_details = state.get("job_description", "")

        system_prompt = """You are a rigorous, unbiased ATS specialist and technical recruiter.

Your task is to do a THOROUGH, word-by-word analysis comparing a candidate's resume to a job description.

CRITICAL RULES:
1. Only list skills in 'missing_skills' if they are EXPLICITLY required by the JD AND absent from the resume. Do NOT hallucinate or infer skills not mentioned.
2. Separate what is "required" from what is "nice to have / preferred / bonus" — treat them in different fields.
3. For 'present_skills', identify every JD requirement that IS covered by the resume (builds confidence).
4. For match_score: 100 = perfect match, 0 = totally unrelated. Be accurate, not generous.
5. In rationale, summarize the REAL gaps and strengths honestly in 2-3 sentences.
6. If the JD says "Nice to have: X" or "Preferred: X" or "Bonus: X", put X in nice_to_have_missing, NOT in missing_skills.
7. Count jd_mentions carefully — how many times a skill appears reinforces its importance.
8. Be strict about what's actually in the resume text vs. what you're assuming."""

        result = await structured_generate(
            SkillGapAnalysis,
            [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"=== RESUME ===\n{(base_resume or '')[:4000]}\n\n"
                        f"=== JOB DESCRIPTION ===\n{(job_details or '')[:5000]}\n\n"
                        "Now perform a thorough word-by-word match analysis. "
                        "Be strict — only include skills that are actually mentioned in the JD. "
                        "Do not add skills based on what is 'typical' for the role."
                    ),
                },
            ],
            fallback=self._mock,
        )
        return {"skill_gap": result.model_dump()}


agent_registry.register(SkillGapAgent())
