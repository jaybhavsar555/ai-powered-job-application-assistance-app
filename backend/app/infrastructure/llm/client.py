"""
Shared OpenAI-compatible LLM client.

Active provider (OpenAI cloud / Ollama / mock) comes from runtime config so
Canvas can switch without restarting the API process.
"""
from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
import instructor
from openai import AsyncOpenAI

from app.infrastructure.llm.runtime import get_llm_runtime
from app.infrastructure.llm.telemetry import (
    record_llm_call,
    record_llm_failure,
    record_llm_success,
    record_mock_fallback,
)

_ollama_session_warmed = False


@lru_cache()
def get_raw_openai_client() -> Optional[AsyncOpenAI]:
    cfg = get_llm_runtime()
    if cfg.force_mock:
        return None
    if cfg.provider in ("openai", "tokenharbor") and not cfg.api_key:
        return None

    kwargs: dict[str, Any] = {
        "api_key": cfg.api_key or "ollama",
        # Read timeout must cover full local generation; connect stays snappy.
        "timeout": httpx.Timeout(cfg.timeout_seconds, connect=10.0),
        # Fail fast on 502 so Token Harbor can switch to the alt free model.
        "max_retries": 0,
    }
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    return AsyncOpenAI(**kwargs)


@lru_cache()
def get_instructor_client():
    """
    Instructor-wrapped client for structured (Pydantic) responses.
    Local/OpenAI-compatible servers (Ollama) use JSON mode; OpenAI cloud prefers tool calling.
    """
    raw = get_raw_openai_client()
    if raw is None:
        return None

    cfg = get_llm_runtime()
    mode = instructor.Mode.JSON if cfg.use_local_json_mode else instructor.Mode.TOOLS
    return instructor.from_openai(raw, mode=mode)


def get_llm_model() -> str:
    return get_llm_runtime().model


def llm_enabled() -> bool:
    cfg = get_llm_runtime()
    if cfg.force_mock:
        return False
    return get_instructor_client() is not None


def _ollama_native_base(openai_compat_base: str) -> str:
    """http://host:11434/v1 → http://host:11434"""
    parsed = urlparse(openai_compat_base or "http://localhost:11434/v1")
    root = f"{parsed.scheme}://{parsed.netloc}" if parsed.scheme and parsed.netloc else "http://localhost:11434"
    return root.rstrip("/")


async def warm_ollama_model(cfg=None) -> dict[str, Any]:
    """
    Load the active Ollama model into memory and pin it with keep_alive.
    Call when switching to Ollama so the first workflow agent is not a cold start.
    """
    cfg = cfg or get_llm_runtime()
    if cfg.provider != "ollama":
        return {"warmed": False, "reason": "not_ollama"}

    native = _ollama_native_base(cfg.base_url)
    payload = {
        "model": cfg.model,
        "prompt": "ok",
        "stream": False,
        "keep_alive": cfg.keep_alive or "30m",
        "options": {
            "num_predict": 1,
            "num_ctx": min(cfg.num_ctx or 512, 512),
        },
    }
    if cfg.num_thread and cfg.num_thread > 0:
        payload["options"]["num_thread"] = cfg.num_thread

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0)) as client:
            resp = await client.post(f"{native}/api/generate", json=payload)
            resp.raise_for_status()
        print(f"[LLM] warmed ollama model={cfg.model} keep_alive={cfg.keep_alive}")
        return {"warmed": True, "model": cfg.model, "keep_alive": cfg.keep_alive}
    except Exception as exc:
        print(f"[LLM] ollama warm failed ({type(exc).__name__}: {exc})")
        return {"warmed": False, "error": str(exc), "model": cfg.model}


async def structured_generate(
    response_model,
    messages,
    *,
    fallback=None,
    max_tokens: int | None = None,
    timeout: float | None = None,
):
    """
    Run Instructor structured generation.

    - Explicit mock mode (provider=mock / LLM_FORCE_MOCK): uses ``fallback`` only.
    - Otherwise: real LLM only. Failures raise RuntimeError (no silent fake JSON).
    - Token Harbor / OpenAI may fall through to local Ollama (real model), then raise.
    """
    cfg = get_llm_runtime()
    record_llm_call()

    if cfg.force_mock:
        if fallback is None:
            raise RuntimeError(
                "Mock LLM mode is on (LLM_FORCE_MOCK or provider=mock) but this "
                "call has no fallback factory. Turn mock off or fix the agent."
            )
        record_mock_fallback(reason="force_mock", provider=cfg.provider, model=cfg.model)
        print(
            f"[LLM] MOCK MODE — returning synthetic data "
            f"(provider={cfg.provider} model={cfg.model}). "
            "Switch to Ollama/OpenAI for real output."
        )
        return fallback() if callable(fallback) else fallback

    client = get_instructor_client()
    if client is None:
        raise RuntimeError(
            f"LLM provider '{cfg.provider}' is not configured. "
            "Set OPENAI_API_KEY or run Ollama and choose provider=ollama "
            "(Canvas LLM switch). Mock/fake agent output is disabled."
        )

    global _ollama_session_warmed
    if cfg.provider == "ollama" and not _ollama_session_warmed:
        warm = await warm_ollama_model(cfg)
        _ollama_session_warmed = bool(warm.get("warmed"))
        if not _ollama_session_warmed:
            print(
                f"[LLM] ollama warm skipped/failed — first call may hit "
                f"timeout ({cfg.timeout_seconds}s): {warm}"
            )

    model = cfg.model
    call_timeout = float(timeout) if timeout is not None else float(cfg.timeout_seconds)
    token_budget = max_tokens if max_tokens is not None else cfg.max_tokens
    if cfg.provider == "ollama":
        token_budget = min(token_budget, cfg.max_tokens)

    call_messages = list(messages)
    if cfg.provider == "ollama" and call_messages:
        speed_hint = (
            "Respond with compact JSON only. Prefer short strings and small arrays. "
            f"Stay well under {token_budget} tokens."
        )
        first = call_messages[0]
        if first.get("role") == "system":
            call_messages[0] = {
                **first,
                "content": f"{first.get('content', '')}\n\n{speed_hint}".strip(),
            }
        else:
            call_messages.insert(0, {"role": "system", "content": speed_hint})

    create_kwargs: dict[str, Any] = {
        "model": model,
        "response_model": response_model,
        "messages": call_messages,
        "max_retries": 0,
        "max_tokens": token_budget,
        "temperature": 0.2,
    }
    if cfg.provider == "ollama":
        extra = cfg.ollama_extra_body()
        extra["options"]["num_predict"] = token_budget
        create_kwargs["extra_body"] = extra

    last_error: Exception | None = None

    try:
        print(
            f"[LLM] provider={cfg.provider} model={model} "
            f"max_tokens={token_budget} timeout={call_timeout}s"
        )
        result = await asyncio.wait_for(
            client.chat.completions.create(**create_kwargs),
            timeout=call_timeout,
        )
        record_llm_success()
        return result
    except Exception as exc:
        last_error = exc
        detail = _friendly_llm_error(exc, timeout=call_timeout)
        print(
            f"[LLM] provider={cfg.provider} model={model} failed "
            f"({type(exc).__name__}: {detail})"
        )

    # Token Harbor peak-demand / model blip → try another free chat model (real, not mock)
    if cfg.provider == "tokenharbor" and last_error is not None:
        alt = (
            "deepseek-v4-flash:free"
            if "kimi" in (model or "").lower()
            else "kimi-k3:free"
        )
        if alt != model:
            try:
                print(f"[LLM] Token Harbor retry with alternate free model={alt}")
                alt_kwargs = {**create_kwargs, "model": alt}
                result = await asyncio.wait_for(
                    client.chat.completions.create(**alt_kwargs),
                    timeout=min(call_timeout, 60.0),
                )
                record_llm_success()
                return result
            except Exception as alt_exc:
                print(f"[LLM] Token Harbor alt model also failed: {alt_exc}")
                last_error = alt_exc

    # Local Ollama when cloud providers fail (OpenAI or Token Harbor)
    if cfg.provider in ("openai", "tokenharbor"):
        try:
            from app.core.config import get_settings

            settings = get_settings()
            ollama_client = AsyncOpenAI(
                api_key="ollama",
                base_url=settings.OLLAMA_BASE_URL,
                timeout=httpx.Timeout(settings.OLLAMA_TIMEOUT_SECONDS, connect=10.0),
                max_retries=0,
            )
            ollama_inst = instructor.from_openai(
                ollama_client, mode=instructor.Mode.JSON
            )
            ollama_model = settings.OLLAMA_MODEL
            ollama_budget = min(token_budget, int(settings.OLLAMA_MAX_TOKENS or 400))
            print(
                f"[LLM] {cfg.provider} failed — trying real Ollama fallback "
                f"model={ollama_model} (not mock)"
            )
            ollama_kwargs: dict[str, Any] = {
                "model": ollama_model,
                "response_model": response_model,
                "messages": call_messages,
                "max_retries": 0,
                "max_tokens": ollama_budget,
                "temperature": 0.2,
                "extra_body": {
                    "options": {
                        "num_predict": ollama_budget,
                        "num_ctx": min(settings.OLLAMA_NUM_CTX, 2048),
                    }
                },
            }
            result = await asyncio.wait_for(
                ollama_inst.chat.completions.create(**ollama_kwargs),
                timeout=min(float(settings.OLLAMA_TIMEOUT_SECONDS or 120), 120.0),
            )
            record_llm_success()
            return result
        except Exception as inner_exc:
            print(f"[LLM] Ollama fallback also failed: {inner_exc}")
            last_error = inner_exc

    detail = _friendly_llm_error(last_error, timeout=call_timeout) if last_error else "unknown"
    record_llm_failure(
        reason=type(last_error).__name__ if last_error else "unknown",
        provider=cfg.provider,
        model=model,
    )

    # Agents that pass fallback= opt into degraded (real template) output when LLM is down.
    # Not the same as mock mode — logs as degraded, never silent fake success without a fallback.
    if fallback is not None:
        print(
            f"[LLM] degraded — using agent fallback "
            f"(provider={cfg.provider} model={model}): {detail}"
        )
        return fallback() if callable(fallback) else fallback

    raise RuntimeError(
        f"LLM unavailable (provider={cfg.provider} model={model}): {detail}. "
        "Fix OpenAI billing/key, warm Ollama, or raise OLLAMA_TIMEOUT_SECONDS. "
        "No fake/mock content was generated."
    )


def _friendly_llm_error(exc: Exception | None, *, timeout: float | None = None) -> str:
    if exc is None:
        return "unknown error"
    text = str(exc) or type(exc).__name__
    low = text.lower()
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError)) or "timeout" in low:
        secs = f"{int(timeout)}s" if timeout else "the configured timeout"
        return (
            f"Timed out after {secs}. First Ollama call can be slow (model load). "
            "Retry once, use Canvas → warm/switch Ollama, or set "
            "OLLAMA_TIMEOUT_SECONDS=180+ in Compose/.env."
        )
    if "502" in low or "peak demand" in low or "upstream_error" in low:
        return (
            "Token Harbor / upstream is busy (HTTP 502). Retry in a moment, "
            "or set TOKENHARBOR_MODEL=deepseek-v4-flash:free in backend/.env."
        )
    if "insufficient_quota" in low or "no credits" in low or "429" in low:
        return (
            "OpenAI account has no credits (HTTP 429). "
            "Add billing at platform.openai.com or switch to Ollama."
        )
    if "connection" in low and "error" in low:
        return (
            f"{text} — often a billing/network issue; verify API key and "
            "try Ollama locally."
        )
    return f"{type(exc).__name__}: {text}"
