from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from uuid import UUID
from app.api.dependencies import get_current_user
from app.domain.models import User
from app.application.services.workflow import WorkflowService

router = APIRouter()

@router.get("/{job_id}/stream")
async def stream_workflow_execution(
    job_id: UUID,
    current_user: User = Depends(get_current_user)
):
    """
    Server-Sent Events (SSE) endpoint to stream LangGraph execution state updates in real-time.
    """
    service = WorkflowService()
    return StreamingResponse(
        service.stream_workflow(str(job_id), str(current_user.id)),
        media_type="text/event-stream"
    )
