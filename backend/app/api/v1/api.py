from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    knowledge,
    resumes,
    jobs,
    workflows,
    documents,
    applications,
    analytics,
    auth,
    approvals,
    agents,
    marketplace,
    llm,
    inbox,
    companies,
    recruiters,
    messages,
    apply_sessions,
    screening_qa,
    extension,
    apply_prefs,
    obsidian,
)

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(llm.router, prefix="/llm", tags=["llm"])
api_router.include_router(agents.router, prefix="/agents", tags=["agents"])
api_router.include_router(marketplace.router, prefix="/marketplace", tags=["marketplace"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(inbox.router, prefix="/inbox", tags=["inbox"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(recruiters.router, prefix="/recruiters", tags=["recruiters"])
api_router.include_router(messages.router, prefix="/messages", tags=["messages"])
api_router.include_router(
    apply_sessions.router, prefix="/apply-sessions", tags=["apply-sessions"]
)
api_router.include_router(
    screening_qa.router, prefix="/screening-qa", tags=["screening-qa"]
)
api_router.include_router(
    extension.router, prefix="/extension", tags=["extension"]
)
api_router.include_router(
    apply_prefs.router, prefix="/apply-prefs", tags=["apply-prefs"]
)
api_router.include_router(obsidian.router, prefix="/obsidian", tags=["obsidian"])
