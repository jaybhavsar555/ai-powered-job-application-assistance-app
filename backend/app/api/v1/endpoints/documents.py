from fastapi import APIRouter, Depends, Body, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.domain.models import User
from app.application.services.document_generator import DocumentGenerator
from app.application.services.apply_package import ApplyPackageService

router = APIRouter()


class ApplyPackageRequest(BaseModel):
    application_id: Optional[UUID] = None
    job_id: Optional[UUID] = None
    company_name: Optional[str] = Field(
        default=None,
        description="Optional override when job intake missed the company name",
    )


@router.post("/export/docx")
async def export_resume_docx(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
):
    """
    Takes an OptimizedResume JSON payload and compiles it into a downloadable .docx file.
    """
    generator = DocumentGenerator()

    user_name = current_user.email.split("@")[0].capitalize()
    contact_info = current_user.email

    summary = payload.get("summary", "")
    bullets = payload.get("tailored_bullets", [])

    file_stream = generator.generate_docx(user_name, contact_info, summary, bullets)

    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={user_name}_Resume.docx"},
    )


@router.get("/resume-library")
async def resume_library_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List base resumes found under RESUME_SOURCE_DIR."""
    service = ApplyPackageService(db)
    return service.library_status()


@router.post("/apply-package")
async def create_apply_package(
    data: ApplyPackageRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Pick a base resume from the local folder (by Flutter / Full Stack / AI / SDE),
    tailor resume + cover letter to the JD, and write DOCX+PDF into a company folder.
    """
    if not data.application_id and not data.job_id:
        raise HTTPException(status_code=400, detail="Provide application_id or job_id")

    service = ApplyPackageService(db)
    if data.application_id:
        return await service.generate_for_application(
            current_user.id,
            data.application_id,
            company_override=data.company_name,
        )
    return await service.generate_for_job(
        current_user.id,
        data.job_id,  # type: ignore[arg-type]
        company_override=data.company_name,
    )
