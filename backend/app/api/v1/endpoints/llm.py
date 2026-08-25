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


@router.get("/model-presets")
async def list_model_presets(current_user: User = Depends(get_current_user)):
    """
    Recommended local / open models for Career OS agents.
    See docs/local_llm_models.md.
    """
    return {
        "presets": [
            {
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "label": "Qwen 2.5 7B (local)",
                "notes": "Best default for laptop/desktop with 8GB+ RAM. Fully offline.",
                "pull": "ollama pull qwen2.5:7b",
            },
            {
                "provider": "ollama",
                "model": "qwen2.5:3b",
                "label": "Qwen 2.5 3B (light)",
                "notes": "CPU-friendly; default in Docker Compose.",
                "pull": "ollama pull qwen2.5:3b",
            },
            {
                "provider": "ollama",
                "model": "llama3.1:8b",
                "label": "Llama 3.1 8B (local)",
                "notes": "Strong general English for scoring and drafts.",
                "pull": "ollama pull llama3.1:8b",
            },
            {
                "provider": "ollama",
                "model": "deepseek-r1:8b",
                "label": "DeepSeek R1 8B (local)",
                "notes": "Reasoning-heavy evaluations; slower.",
                "pull": "ollama pull deepseek-r1:8b",
            },
            {
                "provider": "tokenharbor",
                "model": "kimi-k3:free",
                "label": "Kimi K3 free (Token Harbor)",
                "notes": "Kimi-class without multi-GPU. Needs TOKENHARBOR_API_KEY.",
                "pull": None,
            },
            {
                "provider": "tokenharbor",
                "model": "deepseek-v4-flash:free",
                "label": "DeepSeek V4 Flash free",
                "notes": "Fast structured JSON via Token Harbor.",
                "pull": None,
            },
            {
                "provider": "ollama",
                "model": "kimi-k2.6:cloud",
                "label": "Kimi K2.6 via Ollama Cloud",
                "notes": "Not local — ollama signin required; weights stay remote.",
                "pull": "ollama run kimi-k2.6:cloud",
            },
        ],
        "docs": "docs/local_llm_models.md",
    }


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
