"""Runtime LLM provider selection (OpenAI cloud vs local Ollama vs mock).

Env defines both profiles; Canvas / API can switch without restarting the process.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Literal, Optional

from app.core.config import get_settings

ProviderName = Literal["openai", "ollama", "mock"]

_lock = Lock()
_active: Optional["LlmRuntimeConfig"] = None


@dataclass(frozen=True)
class LlmRuntimeConfig:
    provider: ProviderName
    model: str
    base_url: str
    api_key: str
    force_mock: bool
    timeout_seconds: float
    max_tokens: int

    @property
    def use_local_json_mode(self) -> bool:
        base = (self.base_url or "").strip().lower()
        return bool(base) and "api.openai.com" not in base


def _infer_boot_provider(settings) -> ProviderName:
    explicit = (getattr(settings, "LLM_PROVIDER", "") or "").strip().lower()
    if explicit in ("openai", "ollama", "mock"):
        return explicit  # type: ignore[return-value]
    if getattr(settings, "LLM_FORCE_MOCK", False):
        return "mock"
    base = (settings.OPENAI_BASE_URL or "").strip().lower()
    if base and "api.openai.com" not in base:
        return "ollama"
    if settings.OPENAI_API_KEY:
        return "openai"
    if (getattr(settings, "OLLAMA_BASE_URL", "") or "").strip():
        return "ollama"
    return "mock"


def build_config(provider: ProviderName, model: Optional[str] = None) -> LlmRuntimeConfig:
    settings = get_settings()
    timeout = float(getattr(settings, "LLM_TIMEOUT_SECONDS", 45) or 45)
    max_tokens = int(getattr(settings, "LLM_MAX_TOKENS", 700) or 700)

    if provider == "mock":
        return LlmRuntimeConfig(
            provider="mock",
            model=model or "mock",
            base_url="",
            api_key="",
            force_mock=True,
            timeout_seconds=timeout,
            max_tokens=max_tokens,
        )

    if provider == "ollama":
        ollama_model = (
            model
            or getattr(settings, "OLLAMA_MODEL", None)
            or "qwen2.5:3b"
        )
        return LlmRuntimeConfig(
            provider="ollama",
            model=ollama_model,
            base_url=(getattr(settings, "OLLAMA_BASE_URL", None) or "http://localhost:11434/v1").rstrip("/"),
            api_key=getattr(settings, "OLLAMA_API_KEY", None) or "ollama",
            force_mock=False,
            timeout_seconds=timeout,
            max_tokens=max_tokens,
        )

    # openai cloud
    openai_model = (
        model
        or getattr(settings, "OPENAI_MODEL", None)
        or settings.LLM_MODEL
        or "gpt-4o"
    )
    # Avoid accidentally using an Ollama tag as the cloud model when LLM_MODEL was local
    if not model and ":" in openai_model and getattr(settings, "OPENAI_MODEL", ""):
        openai_model = settings.OPENAI_MODEL
    elif not model and openai_model.startswith("qwen"):
        openai_model = getattr(settings, "OPENAI_MODEL", None) or "gpt-4o"

    return LlmRuntimeConfig(
        provider="openai",
        model=openai_model,
        base_url="",  # official OpenAI SDK default
        api_key=settings.OPENAI_API_KEY or "",
        force_mock=False,
        timeout_seconds=timeout,
        max_tokens=max_tokens,
    )


def get_llm_runtime() -> LlmRuntimeConfig:
    global _active
    with _lock:
        if _active is None:
            settings = get_settings()
            _active = build_config(_infer_boot_provider(settings))
        return _active


def set_llm_provider(provider: ProviderName, model: Optional[str] = None) -> LlmRuntimeConfig:
    """Switch active provider and invalidate cached OpenAI/Instructor clients."""
    global _active
    cfg = build_config(provider, model=model)
    with _lock:
        _active = cfg

    # Break circular import: clear client caches after mutation
    from app.infrastructure.llm import client as llm_client

    llm_client.get_raw_openai_client.cache_clear()
    llm_client.get_instructor_client.cache_clear()
    return cfg


def runtime_status() -> dict:
    cfg = get_llm_runtime()
    settings = get_settings()
    return {
        "provider": cfg.provider,
        "model": cfg.model,
        "base_url": cfg.base_url or None,
        "force_mock": cfg.force_mock,
        "timeout_seconds": cfg.timeout_seconds,
        "max_tokens": cfg.max_tokens,
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "ollama_base_url": getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "openai_model_default": getattr(settings, "OPENAI_MODEL", None) or "gpt-4o",
        "ollama_model_default": getattr(settings, "OLLAMA_MODEL", None) or "qwen2.5:3b",
        "profiles": {
            "openai": {
                "model": getattr(settings, "OPENAI_MODEL", None) or "gpt-4o",
                "base_url": None,
                "ready": bool(settings.OPENAI_API_KEY),
            },
            "ollama": {
                "model": getattr(settings, "OLLAMA_MODEL", None) or "qwen2.5:3b",
                "base_url": getattr(settings, "OLLAMA_BASE_URL", None) or "http://localhost:11434/v1",
                "ready": True,
            },
            "mock": {
                "model": "mock",
                "base_url": None,
                "ready": True,
            },
        },
    }
