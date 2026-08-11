from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.api.dependencies import get_current_user
from app.domain.models import User
from app.infrastructure.llm.client import warm_ollama_model
from app.infrastructure.llm.runtime import runtime_status, set_llm_provider
from app.infrastructure.llm.telemetry import telemetry_snapshot

router = APIRouter()


class LlmProviderUpdate(BaseModel):
    provider: Literal["openai", "tokenharbor", "ollama", "mock"]
    model: Optional[str] = Field(
        default=None,
        description="Optional model override (e.g. openai/gpt-4o-mini, qwen2.5:3b, th-orchestra)",
    )


@router.get("/provider")
async def get_llm_provider(current_user: User = Depends(get_current_user)):
    """Current LLM provider used by Canvas / agents."""
    return {**runtime_status(), "telemetry": telemetry_snapshot()}


@router.get("/telemetry")
async def get_llm_telemetry(current_user: User = Depends(get_current_user)):
    """Counters for intentional mock mode / LLM hard-fail telemetry."""
    return telemetry_snapshot()


@router.put("/provider")
async def update_llm_provider(
    data: LlmProviderUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Switch workflow LLM between OpenAI, Token Harbor, and local Ollama.
    Mock is rejected unless LLM_ALLOW_MOCK / LLM_FORCE_MOCK is enabled.
    """
    status = runtime_status()
    if data.provider == "openai" and not status["openai_configured"]:
        raise HTTPException(
            status_code=400,
            detail="OPENAI_API_KEY is not set in backend/.env",
        )
    if data.provider == "tokenharbor" and not status.get("tokenharbor_configured"):
        raise HTTPException(
            status_code=400,
            detail="TOKENHARBOR_API_KEY is not set in backend/.env",
        )

    try:
        cfg = set_llm_provider(data.provider, model=data.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    warm_result = None
    if cfg.provider == "ollama":
        warm_result = await warm_ollama_model(cfg)
        if not warm_result.get("warmed"):
            background_tasks.add_task(warm_ollama_model, cfg)

    settings = get_settings()
    return {
        **runtime_status(),
        "message": f"LLM provider set to {cfg.provider} ({cfg.model})",
        "warm": warm_result,
        "mock_allowed": bool(settings.LLM_ALLOW_MOCK or settings.LLM_FORCE_MOCK),
    }
