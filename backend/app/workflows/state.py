from typing import TypedDict, Annotated, Dict, Any, Optional
import operator

class AgentState(TypedDict):
    job_id: str
    user_id: str
    resume_id: Optional[str]
    messages: Annotated[list, operator.add]
    job_details: Dict[str, Any]
    company_research: Dict[str, Any]
    ats_score: Optional[int]
    tailored_resume: Dict[str, Any]
    cover_letter: Optional[str]
    requires_human_approval: bool
