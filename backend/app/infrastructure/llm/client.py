"""
Shared OpenAI-compatible LLM client.

Active provider (OpenAI cloud / Ollama / mock) comes from runtime config so
Canvas can switch without restarting the API process.
"""
from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any, Optional

import httpx
import instructor
from openai import AsyncOpenAI

from app.infrastructure.llm.runtime import get_llm_runtime


@lru_cache()
def get_raw_openai_client() -> Optional[AsyncOpenAI]:
    cfg = get_llm_runtime()
    if cfg.force_mock:
        return None
    if cfg.provider == "openai" and not cfg.api_key:
        return None

    kwargs: dict[str, Any] = {
        "api_key": cfg.api_key or "ollama",
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


async def structured_generate(response_model, messages, *, fallback):
    """
    Run Instructor structured generation. On missing model / Ollama errors / timeout,
    return the fallback instance so workflows stay demoable on CPU-only hosts.
    """
    cfg = get_llm_runtime()
    if cfg.force_mock:
        print(f"[LLM] provider=mock — using mock")
        return fallback() if callable(fallback) else fallback

    client = get_instructor_client()
    if client is None:
        print(f"[LLM] provider={cfg.provider} not configured — using mock")
        return fallback() if callable(fallback) else fallback

    model = cfg.model
    timeout = cfg.timeout_seconds
    max_tokens = cfg.max_tokens

    try:
        print(f"[LLM] provider={cfg.provider} model={model}")
        return await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                response_model=response_model,
                messages=messages,
                max_retries=0,
                max_tokens=max_tokens,
                temperature=0.2,
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        print(f"[LLM] provider={cfg.provider} model={model} timed out after {timeout}s — falling back to mock")
        return fallback() if callable(fallback) else fallback
    except Exception as exc:
        print(
            f"[LLM] provider={cfg.provider} model={model} "
            f"Falling back to mock ({type(exc).__name__}: {exc})"
        )
        return fallback() if callable(fallback) else fallback
