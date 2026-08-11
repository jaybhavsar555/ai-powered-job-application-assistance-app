"""Runtime LLM provider selection (OpenAI / Token Harbor / Ollama / mock).

Env defines profiles; Canvas / API can switch without restarting the process.
"""
from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any, Literal, Optional

from app.core.config import get_settings

ProviderName = Literal["openai", "tokenharbor", "ollama", "mock"]

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
    num_ctx: int = 0
    keep_alive: str = ""
    num_thread: int = 0

    @property
    def use_local_json_mode(self) -> bool:
        """Instructor JSON mode for non-official-OpenAI endpoints (Ollama, Token Harbor)."""
        base = (self.base_url or "").strip().lower()
        if not base:
            return False
        return "api.openai.com" not in base

    def ollama_extra_body(self) -> dict[str, Any]:
        """Options that keep local models warm and completions bounded."""
        options: dict[str, Any] = {
            "num_predict": self.max_tokens,
            "temperature": 0.2,
        }
        if self.num_ctx > 0:
            options["num_ctx"] = self.num_ctx
        if self.num_thread and self.num_thread > 0:
            options["num_thread"] = self.num_thread
        body: dict[str, Any] = {"options": options}
        if self.keep_alive:
            body["keep_alive"] = self.keep_alive
        return body


def _infer_boot_provider(settings) -> ProviderName:
    explicit = (getattr(settings, "LLM_PROVIDER", "") or "").strip().lower()
    if explicit in ("openai", "tokenharbor", "ollama", "mock"):
        return explicit  # type: ignore[return-value]
    if getattr(settings, "LLM_FORCE_MOCK", False):
        return "mock"
    if (getattr(settings, "TOKENHARBOR_API_KEY", "") or "").strip():
        return "tokenharbor"
    base = (settings.OPENAI_BASE_URL or "").strip().lower()
    if base and "api.openai.com" not in base and "tokenharbor" not in base:
        return "ollama"
    if settings.OPENAI_API_KEY:
        return "openai"
    if (getattr(settings, "OLLAMA_BASE_URL", "") or "").strip():
        return "ollama"
    return "mock"


def build_config(provider: ProviderName, model: Optional[str] = None) -> LlmRuntimeConfig:
    settings = get_settings()
    cloud_timeout = float(getattr(settings, "LLM_TIMEOUT_SECONDS", 45) or 45)
    cloud_max_tokens = int(getattr(settings, "LLM_MAX_TOKENS", 700) or 700)

    if provider == "mock":
        return LlmRuntimeConfig(
            provider="mock",
            model=model or "mock",
            base_url="",
            api_key="",
            force_mock=True,
            timeout_seconds=cloud_timeout,
            max_tokens=cloud_max_tokens,
        )

    if provider == "ollama":
        ollama_model = (
            model
            or getattr(settings, "OLLAMA_MODEL", None)
            or "qwen2.5:3b"
        )
        ollama_timeout = float(
            getattr(settings, "OLLAMA_TIMEOUT_SECONDS", None)
            or cloud_timeout
            or 90
        )
        ollama_max = int(
            getattr(settings, "OLLAMA_MAX_TOKENS", None)
            or min(cloud_max_tokens, 200)
            or 200
        )
        return LlmRuntimeConfig(
            provider="ollama",
            model=ollama_model,
            base_url=(getattr(settings, "OLLAMA_BASE_URL", None) or "http://localhost:11434/v1").rstrip("/"),
            api_key=getattr(settings, "OLLAMA_API_KEY", None) or "ollama",
            force_mock=False,
            timeout_seconds=ollama_timeout,
            max_tokens=ollama_max,
            num_ctx=int(getattr(settings, "OLLAMA_NUM_CTX", 2048) or 2048),
            keep_alive=str(getattr(settings, "OLLAMA_KEEP_ALIVE", None) or "30m"),
            num_thread=int(getattr(settings, "OLLAMA_NUM_THREAD", 0) or 0),
        )

    if provider == "tokenharbor":
        th_model = (
            model
            or getattr(settings, "TOKENHARBOR_MODEL", None)
            or "kimi-k3:free"
        )
        th_timeout = float(
            getattr(settings, "TOKENHARBOR_TIMEOUT_SECONDS", None) or cloud_timeout or 90
        )
        th_max = int(
            getattr(settings, "TOKENHARBOR_MAX_TOKENS", None) or cloud_max_tokens or 1200
        )
        return LlmRuntimeConfig(
            provider="tokenharbor",
            model=th_model,
            base_url=(
                getattr(settings, "TOKENHARBOR_BASE_URL", None) or "https://tokenharbor.ai/v1"
            ).rstrip("/"),
            api_key=(getattr(settings, "TOKENHARBOR_API_KEY", None) or "").strip(),
            force_mock=False,
            timeout_seconds=th_timeout,
            max_tokens=th_max,
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
        base_url=(settings.OPENAI_BASE_URL or "").rstrip("/"),
        api_key=settings.OPENAI_API_KEY or "",
        force_mock=False,
        timeout_seconds=cloud_timeout,
        max_tokens=cloud_max_tokens,
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
    settings = get_settings()
    if provider == "mock" and not (
        getattr(settings, "LLM_ALLOW_MOCK", False) or getattr(settings, "LLM_FORCE_MOCK", False)
    ):
        raise ValueError(
            "Mock LLM is disabled (LLM_ALLOW_MOCK=false). "
            "Use OpenAI, Token Harbor, or Ollama so failures are visible — not fake agent output. "
            "Set LLM_ALLOW_MOCK=true only for intentional demos/tests."
        )
    if provider == "tokenharbor" and not (getattr(settings, "TOKENHARBOR_API_KEY", "") or "").strip():
        raise ValueError(
            "TOKENHARBOR_API_KEY is not set. Add it to backend/.env "
            "(https://tokenharbor.ai/dashboard/api-keys)."
        )

    cfg = build_config(provider, model=model)
    with _lock:
        _active = cfg

    from app.infrastructure.llm import client as llm_client

    llm_client.get_raw_openai_client.cache_clear()
    llm_client.get_instructor_client.cache_clear()
    llm_client._ollama_session_warmed = False
    return cfg


def runtime_status() -> dict:
    cfg = get_llm_runtime()
    settings = get_settings()
    th_key = bool((getattr(settings, "TOKENHARBOR_API_KEY", "") or "").strip())
    return {
        "provider": cfg.provider,
        "model": cfg.model,
        "base_url": cfg.base_url or None,
        "force_mock": cfg.force_mock,
        "mock_allowed": bool(
            getattr(settings, "LLM_ALLOW_MOCK", False)
            or getattr(settings, "LLM_FORCE_MOCK", False)
        ),
        "timeout_seconds": cfg.timeout_seconds,
        "max_tokens": cfg.max_tokens,
        "num_ctx": cfg.num_ctx or None,
        "keep_alive": cfg.keep_alive or None,
        "openai_configured": bool(settings.OPENAI_API_KEY),
        "tokenharbor_configured": th_key,
        "ollama_base_url": getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        "openai_model_default": getattr(settings, "OPENAI_MODEL", None) or "gpt-4o",
        "tokenharbor_model_default": getattr(settings, "TOKENHARBOR_MODEL", None)
        or "kimi-k3:free",
        "ollama_model_default": getattr(settings, "OLLAMA_MODEL", None) or "qwen2.5:3b",
        "profiles": {
            "openai": {
                "model": getattr(settings, "OPENAI_MODEL", None) or "gpt-4o",
                "base_url": None,
                "ready": bool(settings.OPENAI_API_KEY),
            },
            "tokenharbor": {
                "model": getattr(settings, "TOKENHARBOR_MODEL", None) or "kimi-k3:free",
                "base_url": getattr(settings, "TOKENHARBOR_BASE_URL", None)
                or "https://tokenharbor.ai/v1",
                "ready": th_key,
            },
            "ollama": {
                "model": getattr(settings, "OLLAMA_MODEL", None) or "qwen2.5:3b",
                "base_url": getattr(settings, "OLLAMA_BASE_URL", None) or "http://localhost:11434/v1",
                "max_tokens": int(getattr(settings, "OLLAMA_MAX_TOKENS", 200) or 200),
                "num_ctx": int(getattr(settings, "OLLAMA_NUM_CTX", 2048) or 2048),
                "keep_alive": str(getattr(settings, "OLLAMA_KEEP_ALIVE", None) or "30m"),
                "ready": True,
            },
            "mock": {
                "model": "mock",
                "base_url": None,
                "ready": bool(
                    getattr(settings, "LLM_ALLOW_MOCK", False)
                    or getattr(settings, "LLM_FORCE_MOCK", False)
                ),
            },
        },
    }
