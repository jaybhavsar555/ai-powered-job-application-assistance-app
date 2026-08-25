"""Unified ATS scoring for Tailor, Canvas, and Approvals."""

from __future__ import annotations

from typing import Any, Literal, Optional

from app.application.agents.skill_gap_agent import (
    SkillGapAgent,
    SkillGapAnalysis,
    heuristic_skill_gap,
)
from app.application.services.resume_parser import (
    parse_resume_text,
    run_parser_checks,
    structured_resume_to_text,
)
from app.schemas.ats import ParserATSReport, UnifiedATSResult


def _blend_scores(llm_score: int, parser_score: int) -> int:
    """Weight LLM/heuristic match higher; parser adjusts for ATS formatting."""
    blended = int(round(0.78 * llm_score + 0.22 * parser_score))
    return max(0, min(100, blended))


class ATSService:
    """Single entry point for resume ↔ JD scoring."""

    def __init__(self) -> None:
        self._agent = SkillGapAgent()

    async def analyze(
        self,
        resume_text: str,
        job_description: str,
        *,
        structured_content: Optional[dict[str, Any]] = None,
    ) -> UnifiedATSResult:
        """
        Score resume against JD using LLM (SkillGapAgent) + parser checks.
        Accepts plain text or structured OptimizedResume dict.
        """
        text = (resume_text or "").strip()
        if structured_content and not text:
            text = structured_resume_to_text(structured_content)
        if not text.strip():
            empty_parser = ParserATSReport(
                overall_parser_score=20,
                warnings=["No resume content to score."],
                suggestions=["Upload or paste a resume before analyzing."],
            )
            gap = SkillGapAnalysis(
                match_score=0,
                rationale="No resume text provided.",
                missing_skills=[],
            )
            return UnifiedATSResult.from_skill_gap(
                gap,
                analysis_mode="heuristic",
                parser_checks=empty_parser,
                blended_score=0,
            )

        parsed = parse_resume_text(text)
        parser_checks = run_parser_checks(parsed, job_description or "")

        payload = await self._agent.run(
            {
                "resume_json": text[:12000],
                "job_description": (job_description or "")[:12000],
            }
        )
        gap_dict = payload.get("skill_gap") or {}
        gap = SkillGapAnalysis.model_validate(gap_dict)
        mode: Literal["llm", "heuristic"] = payload.get("analysis_mode") or "heuristic"
        llm_error = payload.get("llm_error")

        blended = _blend_scores(gap.match_score, parser_checks.overall_parser_score)
        return UnifiedATSResult.from_skill_gap(
            gap,
            analysis_mode=mode,
            llm_error=llm_error,
            parser_checks=parser_checks,
            blended_score=blended,
        )

    def analyze_heuristic(
        self,
        resume_text: str,
        job_description: str,
    ) -> UnifiedATSResult:
        """Offline-only scoring (no LLM)."""
        text = (resume_text or "").strip()
        parsed = parse_resume_text(text)
        parser_checks = run_parser_checks(parsed, job_description or "")
        gap = heuristic_skill_gap(text, job_description or "")
        blended = _blend_scores(gap.match_score, parser_checks.overall_parser_score)
        return UnifiedATSResult.from_skill_gap(
            gap,
            analysis_mode="heuristic",
            parser_checks=parser_checks,
            blended_score=blended,
        )

    def to_legacy_ats_score(self, result: UnifiedATSResult) -> dict[str, Any]:
        """Shape expected by LangGraph nodes and older clients."""
        return {
            "score": result.score,
            "matching_skills": result.matching_skills,
            "missing_skills": result.missing_skills,
            "recommendation": result.recommendation,
        }

    def to_skill_gap_payload(self, result: UnifiedATSResult) -> dict[str, Any]:
        """Shape expected by Tailor frontend."""
        return {
            "match_score": result.score,
            "rationale": result.rationale,
            "missing_skills": result.missing_skills,
            "skill_impacts": [i.model_dump() for i in result.skill_impacts],
            "present_skills": [p.model_dump() for p in result.present_skills],
            "nice_to_have_missing": [n.model_dump() for n in result.nice_to_have_missing],
            "qualifications_match": result.qualifications_match,
            "parser_checks": result.parser_checks.model_dump(),
            "llm_score": result.llm_score,
            "parser_score": result.parser_score,
        }
