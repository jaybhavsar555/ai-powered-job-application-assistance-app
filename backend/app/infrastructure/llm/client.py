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
    record_llm_success,
    record_mock_fallback,
)


@lru_cache()
def get_raw_openai_client() -> Optional[AsyncOpenAI]:
    cfg = get_llm_runtime()
    if cfg.force_mock:
        return None
    if cfg.provider == "openai" and not cfg.api_key:
        return None

    kwargs: dict[str, Any] = {
        "api_key": cfg.api_key or "ollama",
        # Read timeout must cover full local generation; connect stays snappy.
        "timeout": httpx.Timeout(cfg.timeout_seconds, connect=10.0),
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


async def structured_generate(response_model, messages, *, fallback, max_tokens: int | None = None):
    """
    Run Instructor structured generation. On missing model / Ollama errors / timeout,
    return the fallback instance so workflows stay demoable on CPU-only hosts.
    Every mock path is logged + counted (`llm_mock_fallback` telemetry).
    """
    cfg = get_llm_runtime()
    record_llm_call()

    if cfg.force_mock:
        record_mock_fallback(reason="force_mock", provider=cfg.provider, model=cfg.model)
        return fallback() if callable(fallback) else fallback

    client = get_instructor_client()
    if client is None:
        record_mock_fallback(
            reason="provider_not_configured",
            provider=cfg.provider,
            model=cfg.model,
        )
        return fallback() if callable(fallback) else fallback

    model = cfg.model
    timeout = cfg.timeout_seconds
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

    try:
        print(
            f"[LLM] provider={cfg.provider} model={model} "
            f"max_tokens={token_budget} timeout={timeout}s"
        )
        result = await asyncio.wait_for(
            client.chat.completions.create(**create_kwargs),
            timeout=timeout,
        )
        record_llm_success()
        return result
    except asyncio.TimeoutError:
        record_mock_fallback(reason="timeout", provider=cfg.provider, model=model)
        return fallback() if callable(fallback) else fallback
    except Exception as exc:
        record_mock_fallback(
            reason=type(exc).__name__,
            provider=cfg.provider,
            model=model,
        )
        print(
            f"[LLM] provider={cfg.provider} model={model} "
            f"Falling back to mock ({type(exc).__name__}: {exc})"
        )
        return fallback() if callable(fallback) else fallback
