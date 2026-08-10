from typing import Literal, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.dependencies import get_current_user
from app.domain.models import User
from app.infrastructure.llm.client import warm_ollama_model
from app.infrastructure.llm.runtime import runtime_status, set_llm_provider
from app.infrastructure.llm.telemetry import telemetry_snapshot

router = APIRouter()


class LlmProviderUpdate(BaseModel):
    provider: Literal["openai", "ollama", "mock"]
    model: Optional[str] = Field(
        default=None,
        description="Optional model override (e.g. gpt-4o-mini or qwen2.5:3b)",
    )


@router.get("/provider")
async def get_llm_provider(current_user: User = Depends(get_current_user)):
    """Current LLM provider used by Canvas / agents."""
    return {**runtime_status(), "telemetry": telemetry_snapshot()}


@router.get("/telemetry")
async def get_llm_telemetry(current_user: User = Depends(get_current_user)):
    """Mock-fallback counters — when agents silently used fallback JSON."""
    return telemetry_snapshot()


@router.put("/provider")
async def update_llm_provider(
    data: LlmProviderUpdate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """
    Switch workflow LLM between OpenAI cloud, local Ollama, or mock.
    Applies immediately to the next agent call (no API restart).
    Switching to Ollama also warms the model so the first agent is not a cold load.
    """
    if data.provider == "openai":
        status = runtime_status()
        if not status["openai_configured"]:
            raise HTTPException(
                status_code=400,
                detail="OPENAI_API_KEY is not set in backend/.env",
            )

    cfg = set_llm_provider(data.provider, model=data.model)
    warm_result = None
    if cfg.provider == "ollama":
        # Await warm so the first Simulate does not pay ~8s model load per agent.
        warm_result = await warm_ollama_model(cfg)
        if not warm_result.get("warmed"):
            # Retry once in background if the first attempt failed (Ollama still starting).
            background_tasks.add_task(warm_ollama_model, cfg)

    return {
        **runtime_status(),
        "message": f"LLM provider set to {cfg.provider} ({cfg.model})",
        "warm": warm_result,
    }
