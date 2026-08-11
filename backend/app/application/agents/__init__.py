"""
Agentic modules for workflow ingestion, execution, and document tailoring.
"""
from .base import OSAgent
from .registry import agent_registry

# Import to trigger registration
from .job_intake import JobIntakeAgent
from .company_research import CompanyResearchAgent
from .ats_analyzer import ATSAnalyzerAgent
from .resume_optimizer import ResumeOptimizerAgent
from .cover_letter_agent import CoverLetterAgent
from .recruiter_discovery_agent import RecruiterDiscoveryAgent
from .outreach_draft_agent import OutreachDraftAgent
from .job_discovery_agent import JobDiscoveryAgent
from .skill_gap_agent import SkillGapAgent

# Optional / experimental agents — must not break core imports
try:
    from .hallucination_agent import HallucinationAgent  # noqa: F401
except Exception as exc:  # pragma: no cover
    print(f"[Agents] hallucination_agent skipped: {exc}")

try:
    from .interview_prep_agent import InterviewPrepAgent  # noqa: F401
except Exception as exc:  # pragma: no cover
    print(f"[Agents] interview_prep_agent skipped: {exc}")

__all__ = [
    "CoverLetterAgent",
    "ResumeOptimizerAgent",
    "JobDiscoveryAgent",
    "RecruiterDiscoveryAgent",
    "SkillGapAgent",
]
