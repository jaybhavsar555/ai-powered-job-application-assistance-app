"""Search Pipeline API — approve-at-each-gate job search → apply → email."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.application.services.search_pipeline import SearchPipelineService
from app.domain.models import User

router = APIRouter()


class PipelinePrefs(BaseModel):
    targetRoles: str = "software engineer"
    minSalary: str = "0"
    locationHubs: list[str] = Field(default_factory=lambda: ["Remote"])
    isRemote: bool = True
    companyTypes: list[str] = Field(default_factory=list)
    techStack: str = ""
    experienceLevel: str = ""
    workAuthorization: str = ""


class JobIdsBody(BaseModel):
    job_ids: List[str] = Field(default_factory=list)


class ExecuteAction(BaseModel):
    job_id: str
    approve_apply: bool = False
    approve_email: bool = False
    email_to: Optional[str] = None


class ExecuteBody(BaseModel):
    actions: List[ExecuteAction] = Field(default_factory=list)


@router.get("/stages")
async def list_stages(current_user: User = Depends(get_current_user)):
    from app.application.services.search_pipeline import STAGES

    return {"stages": STAGES}


@router.get("/runs")
async def list_runs(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SearchPipelineService(db)
    return {"runs": svc.list_runs(current_user.id)}


@router.get("/runs/{run_id}")
async def get_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SearchPipelineService(db)
    return svc.get_run(current_user.id, run_id)


@router.post("/scan")
async def start_scan(
    prefs: PipelinePrefs,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Scan Knowledge Vault portals + common boards + open web, score jobs,
    then pause for shortlist approval.
    """
    svc = SearchPipelineService(db)
    try:
        return await svc.start_scan(current_user.id, prefs.model_dump())
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Pipeline scan failed: {type(exc).__name__}: {exc}",
        ) from exc


@router.post("/runs/{run_id}/approve-shortlist")
async def approve_shortlist(
    run_id: str,
    body: JobIdsBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SearchPipelineService(db)
    return svc.approve_shortlist(current_user.id, run_id, body.job_ids)


@router.post("/runs/{run_id}/approve-evaluate")
async def approve_evaluate(
    run_id: str,
    body: JobIdsBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SearchPipelineService(db)
    return await svc.approve_evaluate(current_user.id, run_id, body.job_ids)


@router.post("/runs/{run_id}/approve-execute")
async def approve_execute(
    run_id: str,
    body: ExecuteBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Per-job approve apply and/or email — never silent."""
    svc = SearchPipelineService(db)
    # Allow setting email_to on the run before execute
    run = svc.get_run(current_user.id, run_id)
    by_id = {a.job_id: a for a in body.actions}
    for job in run.get("jobs") or []:
        act = by_id.get(str(job.get("id")))
        if act and act.email_to and job.get("email_draft"):
            job["email_draft"] = {**job["email_draft"], "to": act.email_to.strip()}
    svc._save(current_user.id, run)
    actions: List[Dict[str, Any]] = [
        {
            "job_id": a.job_id,
            "approve_apply": a.approve_apply,
            "approve_email": a.approve_email,
        }
        for a in body.actions
    ]
    return await svc.approve_execute(current_user.id, run_id, actions)
