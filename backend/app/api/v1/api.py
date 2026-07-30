from fastapi import APIRouter
from app.api.v1.endpoints import health, knowledge, resumes, jobs, workflows, documents, applications

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(resumes.router, prefix="/resumes", tags=["resumes"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(applications.router, prefix="/applications", tags=["applications"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
