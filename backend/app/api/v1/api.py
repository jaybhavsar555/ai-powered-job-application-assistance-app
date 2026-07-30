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
