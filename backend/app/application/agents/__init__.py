"""
Agentic modules for workflow ingestion, execution, and document tailoring.
"""
from .base import OSAgent
from .registry import agent_registry

# Import to trigger registration
from .job_intake import JobIntakeAgent
from .ats_analyzer import ATSAnalyzerAgent
from .resume_optimizer import ResumeOptimizerAgent
from .cover_letter_agent import CoverLetterAgent

__all__ = ["OSAgent", "agent_registry"]
