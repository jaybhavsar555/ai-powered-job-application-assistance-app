from fastapi import APIRouter, Depends, Body, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from pathlib import Path
from urllib.parse import quote
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.domain.models import User
from app.application.services.document_generator import DocumentGenerator
from app.application.services.apply_package import ApplyPackageService
from app.core.config import get_settings
from app.infrastructure.resume_library import extract_text
from app.application.services.resume_studio import ResumeStudioService

router = APIRouter()


def _resume_fields_from_payload(payload: dict, user: User) -> tuple[str, str, str, list[str], list[str], Optional[str]]:
    user_name = str(payload.get("user_name") or user.email.split("@")[0].capitalize())
    contact_info = str(payload.get("contact_info") or user.email)
    summary = str(payload.get("summary") or "")
    bullets = list(payload.get("tailored_bullets") or [])
    skills = list(payload.get("added_keywords") or [])
    base_excerpt = payload.get("base_excerpt")
    return user_name, contact_info, summary, bullets, skills, base_excerpt


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
    user_name, contact_info, summary, bullets, skills, base_excerpt = _resume_fields_from_payload(
        payload, current_user
    )

    file_stream = generator.generate_resume_docx(
        user_name, contact_info, summary, bullets, skills=skills, base_excerpt=base_excerpt
    )

    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={user_name}_Resume.docx"},
    )


@router.post("/export/pdf")
async def export_resume_pdf(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
):
    """Compile tailored resume to ATS-friendly PDF (LaTeX first, ReportLab fallback)."""
    generator = DocumentGenerator()
    user_name, contact_info, summary, bullets, skills, base_excerpt = _resume_fields_from_payload(
        payload, current_user
    )

    file_stream, _ = generator.generate_resume_pdf(
        user_name, contact_info, summary, bullets, skills=skills, base_excerpt=base_excerpt
    )

    return StreamingResponse(
        file_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={user_name}_Resume.pdf"},
    )


@router.post("/export/tex")
async def export_resume_tex(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user),
):
    """Return editable LaTeX source for the tailored resume (compile locally or re-upload)."""
    generator = DocumentGenerator()
    user_name, contact_info, summary, bullets, skills, base_excerpt = _resume_fields_from_payload(
        payload, current_user
    )

    tex_content = generator.generate_resume_latex(
        user_name, contact_info, summary, bullets, skills=skills, base_excerpt=base_excerpt
    )

    return StreamingResponse(
        iter([tex_content.encode("utf-8")]),
        media_type="application/x-tex",
        headers={"Content-Disposition": f"attachment; filename={user_name}_Resume.tex"},
    )


class CompileTexRequest(BaseModel):
    tex_content: str = Field(..., min_length=1, max_length=120_000)
    filename: str = Field(default="Tailored_Resume")


@router.post("/compile/tex")
async def compile_tex_to_pdf(
    body: CompileTexRequest,
    current_user: User = Depends(get_current_user),
):
    """Compile edited LaTeX source to PDF (in-browser editor round-trip)."""
    generator = DocumentGenerator()
    try:
        pdf_stream = generator.compile_tex(body.tex_content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    safe_name = "".join(c for c in body.filename if c.isalnum() or c in "._-") or "Resume"
    return StreamingResponse(
        pdf_stream,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={safe_name}.pdf"},
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


@router.get("/package-download")
async def download_package_file(
    application_id: UUID,
    kind: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream DOCX/PDF from a successful apply package only (no invented files)."""
    studio = ResumeStudioService(db)
    path = await studio.resolve_package_file(current_user.id, application_id, kind)
    media = {
        "resume_pdf": "application/pdf",
        "resume_tex": "application/x-tex",
        "cover_pdf": "application/pdf",
        "resume_docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "cover_docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(kind, "application/octet-stream")
    disposition = "inline" if kind.endswith("_pdf") else "attachment"
    quoted = quote(path.name)
    return FileResponse(
        path,
        media_type=media,
        headers={
            "Content-Disposition": f"{disposition}; filename=\"{path.name}\"; filename*=UTF-8''{quoted}",
            "Cache-Control": "private, max-age=60",
            "X-Content-Type-Options": "nosniff",
        },
    )

@router.get("/package-download-job")
async def download_package_file_job(
    folder: str,
    kind: str,
    current_user: User = Depends(get_current_user),
):
    """Stream DOCX/PDF directly from a folder generated by apply-package (for job simulations without app id)."""
    from app.core.config import get_settings
    settings = get_settings()
    out_root = Path(settings.APPLICATION_PACKAGE_DIR).resolve()
    folder_path = Path(folder).resolve()
    
    if out_root not in folder_path.parents and out_root != folder_path:
        raise HTTPException(status_code=403, detail="Folder is outside package directory")
        
    if kind not in ["resume_docx", "resume_pdf", "cover_docx", "cover_pdf"]:
        raise HTTPException(status_code=400, detail="Invalid file kind")
        
    # Find the file that matches the kind
    match = None
    if folder_path.exists():
        for f in folder_path.iterdir():
            if kind == "resume_docx" and f.name.endswith("_Resume.docx"):
                match = f
            elif kind == "resume_pdf" and f.name.endswith("_Resume.pdf"):
                match = f
            elif kind == "cover_docx" and f.name.endswith("_Cover_Letter.docx"):
                match = f
            elif kind == "cover_pdf" and f.name.endswith("_Cover_Letter.pdf"):
                match = f
                
    if not match or not match.is_file():
        raise HTTPException(status_code=404, detail="File not found")
        
    media = {
        "resume_pdf": "application/pdf",
        "cover_pdf": "application/pdf",
        "resume_docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "cover_docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }.get(kind, "application/octet-stream")
    
    disposition = "inline" if kind.endswith("_pdf") else "attachment"
    quoted = quote(match.name)
    return FileResponse(
        match,
        media_type=media,
        headers={
            "Content-Disposition": f"{disposition}; filename=\"{match.name}\"; filename*=UTF-8''{quoted}",
            "Cache-Control": "private, max-age=60",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/package-preview")
async def package_file_preview(
    application_id: UUID,
    kind: str = "resume_pdf",
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview metadata for package resume/cover in the side panel before outreach send."""
    studio = ResumeStudioService(db)
    path = await studio.resolve_package_file(current_user.id, application_id, kind)
    suffix = path.suffix.lower()
    file_url = (
        f"/api/v1/documents/package-download?application_id={application_id}&kind={quote(kind)}"
    )
    if suffix == ".pdf" or kind.endswith("_pdf"):
        return {
            "name": path.name,
            "kind": "pdf",
            "file_url": file_url,
            "text": None,
            "can_inline_preview": True,
            "note": "This is the tailored package resume you’ll attach. Download if the viewer fails.",
        }
    try:
        text = extract_text(path)[:20000]
        note = "Formatted preview of the tailored package file."
    except Exception as exc:
        text = ""
        note = f"Could not extract text ({exc}). Download instead."
    return {
        "name": path.name,
        "kind": "docx" if suffix in {".docx", ".doc"} else "text",
        "file_url": file_url,
        "text": text,
        "can_inline_preview": True,
        "note": note,
    }


def _safe_library_path(filename: str) -> Path:
    """Resolve a resume library filename under RESUME_SOURCE_DIR (no path traversal)."""
    settings = get_settings()
    root = Path(settings.RESUME_SOURCE_DIR).resolve()
    name = Path(filename).name
    if not name or name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")
    path = (root / name).resolve()
    if path != root and root not in path.parents:
        raise HTTPException(status_code=403, detail="File outside resume library")
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {name}")
    return path


@router.get("/library-file")
async def stream_library_file(
    name: str,
    current_user: User = Depends(get_current_user),
):
    """
    Stream a master template with inline disposition for PDFs (iframe-friendly)
    and attachment for DOCX/other.
    """
    path = _safe_library_path(name)
    suffix = path.suffix.lower()
    media = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".doc": "application/msword",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }.get(suffix, "application/octet-stream")
    disposition = "inline" if suffix == ".pdf" else "attachment"
    quoted = quote(path.name)
    return FileResponse(
        path,
        media_type=media,
        headers={
            "Content-Disposition": f"{disposition}; filename=\"{path.name}\"; filename*=UTF-8''{quoted}",
            "Cache-Control": "private, max-age=60",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/library-preview")
async def library_file_preview(
    name: str,
    current_user: User = Depends(get_current_user),
):
    """
    Preview metadata for Resume Studio side panel.
    PDF → use file stream URL in an iframe.
    DOCX/TXT/MD → extracted text (browsers cannot render DOCX natively).
    """
    path = _safe_library_path(name)
    suffix = path.suffix.lower()
    file_url = f"/api/v1/documents/library-file?name={quote(path.name)}"

    if suffix == ".pdf":
        return {
            "name": path.name,
            "kind": "pdf",
            "file_url": file_url,
            "text": None,
            "can_inline_preview": True,
            "note": "PDF opens in the side panel; use Download if the viewer fails.",
        }

    if suffix in {".docx", ".doc", ".txt", ".md"}:
        try:
            text = extract_text(path)[:20000]
            note = (
                "Scaled to fit this panel. Download for exact Word layout."
                if suffix in {".docx", ".doc"}
                else "Text preview."
            )
        except Exception as exc:
            text = ""
            note = f"Could not extract text ({exc}). Download the file instead."
        return {
            "name": path.name,
            "kind": "docx" if suffix in {".docx", ".doc"} else "text",
            "file_url": file_url,
            "text": text or "(No extractable text found in this file.)",
            "can_inline_preview": True,
            "note": note,
        }

    return {
        "name": path.name,
        "kind": "unsupported",
        "file_url": file_url,
        "text": None,
        "can_inline_preview": False,
        "note": "Preview not supported for this type — download instead.",
    }


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    import shutil

    settings = get_settings()
    source_dir = Path(settings.RESUME_SOURCE_DIR)
    source_dir.mkdir(parents=True, exist_ok=True)

    safe_name = Path(file.filename or "upload.bin").name
    file_path = source_dir / safe_name
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {"status": "ok", "filename": safe_name, "url": f"/resumes/{safe_name}"}

