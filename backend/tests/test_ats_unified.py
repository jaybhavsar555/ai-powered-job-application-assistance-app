"""Tests for resume parser and unified ATS blending."""

from app.application.services.resume_parser import (
    parse_resume_text,
    run_parser_checks,
    structured_resume_to_text,
)
from app.application.services.ats_service import ATSService, _blend_scores
from app.application.agents.skill_gap_agent import heuristic_skill_gap
from app.schemas.ats import UnifiedATSResult


def test_parse_sections_and_bullets():
    text = """
Jane Doe
jane@example.com

Professional Summary
Backend engineer with 5 years building FastAPI services.

Experience
• Built REST APIs serving 1M requests/day
• Deployed services on AWS with Docker

Skills
Python, FastAPI, PostgreSQL, Docker
"""
    parsed = parse_resume_text(text)
    assert parsed.contact_email == "jane@example.com"
    assert "summary" in parsed.sections or parsed.raw_text
    assert len(parsed.bullets) >= 1
    assert "Python" in parsed.skills or "FastAPI" in parsed.skills


def test_parser_checks_keyword_density():
    resume = """
Summary
Experienced Python FastAPI developer.

Experience
• Built APIs with FastAPI and PostgreSQL

Skills
Python, FastAPI, Docker
"""
    jd = "Required: Python, FastAPI, PostgreSQL, Docker, Kubernetes"
    parsed = parse_resume_text(resume)
    report = run_parser_checks(parsed, jd)
    assert report.overall_parser_score >= 40
    assert report.keyword_density > 0.5
    assert report.has_summary_section is True


def test_structured_resume_to_text():
    text = structured_resume_to_text(
        {
            "summary": "Backend engineer",
            "tailored_bullets": ["Built FastAPI services"],
            "added_keywords": ["Python", "Docker"],
        }
    )
    assert "Backend engineer" in text
    assert "FastAPI" in text
    assert "Python" in text


def test_heuristic_unified_ats():
    resume = "Python FastAPI developer with Docker experience"
    jd = "Looking for Python FastAPI Docker AWS engineer"
    service = ATSService()
    result = service.analyze_heuristic(resume, jd)
    assert isinstance(result, UnifiedATSResult)
    assert 0 <= result.score <= 100
    assert result.analysis_mode == "heuristic"
    assert result.parser_checks.overall_parser_score >= 0


def test_blend_scores_bounds():
    assert _blend_scores(80, 60) == 76
    assert _blend_scores(100, 100) == 100
    assert _blend_scores(0, 0) == 0


def test_skill_gap_to_unified():
    gap = heuristic_skill_gap(
        "Python FastAPI PostgreSQL",
        "Required Python FastAPI Docker Kubernetes",
    )
    unified = UnifiedATSResult.from_skill_gap(gap, analysis_mode="heuristic")
    assert unified.score == gap.match_score
    assert isinstance(unified.matching_skills, list)
