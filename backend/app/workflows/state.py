from typing import TypedDict, Annotated, Dict, Any, Optional, List
import operator


class AgentState(TypedDict):
    job_id: str
    user_id: str
    resume_id: Optional[str]
    messages: Annotated[list, operator.add]
    job_details: Dict[str, Any]
    job_url: Optional[str]
    company_research: Dict[str, Any]
    ats_score: Optional[int]
    missing_skills: List[str]
    matching_skills: List[str]
    tailored_resume: Dict[str, Any]
    cover_letter: Optional[str]
    requires_human_approval: bool
    recruiter_discovery: Dict[str, Any]
    outreach_draft: Dict[str, Any]
    long_term_memory: List[Dict[str, Any]]
    resume_json: str
    hallucination_report: Dict[str, Any]
