"""In-process counters for LLM mock fallbacks (honest telemetry)."""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger("ai_job_assistant.llm")

_lock = threading.Lock()
_stats: dict[str, Any] = {
    "calls": 0,
    "successes": 0,
    "mock_fallbacks": 0,
    "by_reason": {},
}


def record_llm_call() -> None:
    with _lock:
        _stats["calls"] += 1


def record_llm_success() -> None:
    with _lock:
        _stats["successes"] += 1


def record_mock_fallback(*, reason: str, provider: str, model: str) -> None:
    with _lock:
        _stats["mock_fallbacks"] += 1
        by = _stats["by_reason"]
        by[reason] = int(by.get(reason, 0)) + 1
    logger.warning(
        "llm_mock_fallback reason=%s provider=%s model=%s total_fallbacks=%s",
        reason,
        provider,
        model,
        _stats["mock_fallbacks"],
    )


def telemetry_snapshot() -> dict[str, Any]:
    with _lock:
        return {
            "calls": _stats["calls"],
            "successes": _stats["successes"],
            "mock_fallbacks": _stats["mock_fallbacks"],
            "by_reason": dict(_stats["by_reason"]),
        }
