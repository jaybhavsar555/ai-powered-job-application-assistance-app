"""In-process counters for LLM calls (honest telemetry — no silent mock)."""

from __future__ import annotations

import logging
import threading
from typing import Any

logger = logging.getLogger("ai_job_assistant.llm")

_lock = threading.Lock()
_stats: dict[str, Any] = {
    "calls": 0,
    "successes": 0,
    "failures": 0,
    "mock_fallbacks": 0,
    "by_reason": {},
    "failure_by_reason": {},
}


def record_llm_call() -> None:
    with _lock:
        _stats["calls"] += 1


def record_llm_success() -> None:
    with _lock:
        _stats["successes"] += 1


def record_llm_failure(*, reason: str, provider: str, model: str) -> None:
    """Real provider failed — no mock content was returned."""
    with _lock:
        _stats["failures"] += 1
        by = _stats["failure_by_reason"]
        by[reason] = int(by.get(reason, 0)) + 1
    logger.warning(
        "llm_failure reason=%s provider=%s model=%s total_failures=%s "
        "(no mock fallback — call raised)",
        reason,
        provider,
        model,
        _stats["failures"],
    )


def record_mock_fallback(*, reason: str, provider: str, model: str) -> None:
    """Only when provider=mock / LLM_FORCE_MOCK actually returns synthetic data."""
    with _lock:
        _stats["mock_fallbacks"] += 1
        by = _stats["by_reason"]
        by[reason] = int(by.get(reason, 0)) + 1
    logger.warning(
        "llm_mock_used reason=%s provider=%s model=%s total_mock=%s",
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
            "failures": _stats["failures"],
            "mock_fallbacks": _stats["mock_fallbacks"],
            "by_reason": dict(_stats["by_reason"]),
            "failure_by_reason": dict(_stats["failure_by_reason"]),
        }
