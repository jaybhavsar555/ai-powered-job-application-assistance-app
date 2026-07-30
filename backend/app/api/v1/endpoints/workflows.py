from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from uuid import UUID
from typing import Any, Dict, Optional
from jose import jwt, JWTError

from app.core.config import get_settings
from app.domain.models import User
from app.application.services.workflow import WorkflowService
from app.api.dependencies import get_current_user
from app.infrastructure.checkpoints import checkpointer_status
from app.workflows.graph import graph_backend

router = APIRouter()
settings = get_settings()


def _user_from_token(token: str) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        # EmailStr rejects reserved TLDs like .local — use a valid placeholder for SSE-only User
        return User(
            id=UUID(user_id),
            email="sse@example.com",
            auth_provider="local",
        )
    except HTTPException:
        raise
    except (JWTError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token ({type(exc).__name__})",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token ({type(exc).__name__}: {exc})",
        ) from exc


@router.get("/checkpointer")
async def get_checkpointer_status(current_user: User = Depends(get_current_user)):
    """Report whether workflow checkpoints are durable (Postgres) or in-memory."""
    status_payload = checkpointer_status()
    return {
        **status_payload,
        "graph_backend": graph_backend(),
    }


@router.get("/{job_id}/stream")
async def stream_workflow_execution(
    job_id: UUID,
    token: Optional[str] = Query(
        None,
        description="JWT access token — EventSource cannot set Authorization headers",
    ),
    resume: bool = Query(False, description="Resume from LangGraph checkpoint for this job_id"),
):
    """
    Server-Sent Events (SSE) endpoint to stream LangGraph execution updates.
    Pass `?token=` from the frontend EventSource URL. Use `resume=true` to continue a thread.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token query param for SSE",
        )
    current_user = _user_from_token(token)
    service = WorkflowService()
    return StreamingResponse(
        service.stream_workflow(str(job_id), str(current_user.id), resume=resume),
        media_type="text/event-stream",
    )


@router.get("/{job_id}/checkpoint")
async def get_workflow_checkpoint(
    job_id: UUID,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Inspect LangGraph checkpoint / next nodes for a job thread."""
    service = WorkflowService()
    return await service.get_checkpoint(str(job_id))
