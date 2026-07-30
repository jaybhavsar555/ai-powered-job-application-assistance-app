from fastapi import APIRouter, Depends, Body
from fastapi.responses import StreamingResponse
from app.api.dependencies import get_current_user
from app.domain.models import User
from app.application.services.document_generator import DocumentGenerator

router = APIRouter()

@router.post("/export/docx")
async def export_resume_docx(
    payload: dict = Body(...),
    current_user: User = Depends(get_current_user)
):
    """
    Takes an OptimizedResume JSON payload and compiles it into a downloadable .docx file.
    """
    generator = DocumentGenerator()
    
    # Extract mock profile data based on current user session
    user_name = current_user.email.split('@')[0].capitalize()
    contact_info = current_user.email
    
    # Extract AI-generated content
    summary = payload.get("summary", "")
    bullets = payload.get("tailored_bullets", [])
    
    # Generate Document
    file_stream = generator.generate_docx(user_name, contact_info, summary, bullets)
    
    return StreamingResponse(
        file_stream, 
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={user_name}_Resume.docx"}
    )
