"""Unified ATS scoring schemas used across Tailor, Canvas, and Approvals."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.application.agents.skill_gap_agent import (
    NiceToHaveSkill,
    SkillGapAnalysis,
    SkillImpact,
    SkillPresent,
)


class ParserATSReport(BaseModel):
    """Jobscan-style parser checks (sections, keyword density, formatting)."""

    has_summary_section: bool = False
    has_experience_section: bool = False
    has_skills_section: bool = False
    has_education_section: bool = False
    keyword_density: float = Field(
        0.0, description="Share of JD keywords found anywhere on resume (0–1)"
    )
    keywords_in_summary: int = 0
    keywords_in_skills: int = 0
    keywords_in_experience: int = 0
    formatting_flags: list[str] = Field(default_factory=list)
    section_score: int = Field(0, ge=0, le=100)
    placement_score: int = Field(0, ge=0, le=100)
    overall_parser_score: int = Field(0, ge=0, le=100)
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class UnifiedATSResult(BaseModel):
    """Canonical ATS payload for all surfaces."""

    score: int = Field(..., ge=0, le=100)
    llm_score: int = Field(..., ge=0, le=100)
    parser_score: int = Field(0, ge=0, le=100)
    matching_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    recommendation: str = ""
    rationale: str = ""
    skill_impacts: list[SkillImpact] = Field(default_factory=list)
    present_skills: list[SkillPresent] = Field(default_factory=list)
    nice_to_have_missing: list[NiceToHaveSkill] = Field(default_factory=list)
    qualifications_match: str = ""
    analysis_mode: Literal["llm", "heuristic"] = "heuristic"
    llm_error: Optional[str] = None
    parser_checks: ParserATSReport = Field(default_factory=ParserATSReport)

    def to_workflow_state(self) -> dict:
        """Fields persisted on DBApplication.workflow_state."""
        return {
            "ats_score": self.score,
            "missing_skills": self.missing_skills,
            "matching_skills": self.matching_skills,
            "ats_recommendation": self.recommendation,
            "ats_rationale": self.rationale,
            "ats_parser": self.parser_checks.model_dump(),
            "qualifications_match": self.qualifications_match,
        }

    def to_api_payload(self) -> dict:
        """JSON-safe dict for API responses."""
        return self.model_dump()

    @classmethod
    def from_skill_gap(
        cls,
        gap: SkillGapAnalysis,
        *,
        analysis_mode: Literal["llm", "heuristic"],
        llm_error: Optional[str] = None,
        parser_checks: Optional[ParserATSReport] = None,
        blended_score: Optional[int] = None,
    ) -> "UnifiedATSResult":
        matching = [p.skill for p in gap.present_skills]
        llm_score = max(0, min(100, int(gap.match_score)))
        parser = parser_checks or ParserATSReport()
        parser_score = parser.overall_parser_score
        final = blended_score if blended_score is not None else llm_score
        recommendation = gap.rationale
        if gap.missing_skills:
            top = ", ".join(gap.missing_skills[:4])
            recommendation = (
                f"{gap.rationale} Add or emphasize: {top}."
                if gap.rationale
                else f"Add or emphasize: {top}."
            )
        return cls(
            score=final,
            llm_score=llm_score,
            parser_score=parser_score,
            matching_skills=matching,
            missing_skills=list(gap.missing_skills),
            recommendation=recommendation[:500],
            rationale=gap.rationale,
            skill_impacts=list(gap.skill_impacts),
            present_skills=list(gap.present_skills),
            nice_to_have_missing=list(gap.nice_to_have_missing),
            qualifications_match=gap.qualifications_match,
            analysis_mode=analysis_mode,
            llm_error=llm_error,
            parser_checks=parser,
        )
