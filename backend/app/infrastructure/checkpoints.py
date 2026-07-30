"""Durable LangGraph checkpointer (Postgres) with in-memory fallback."""

from __future__ import annotations

import asyncio
import sys
from typing import Any, Optional

from app.core.config import get_settings

_pool: Any = None
_checkpointer: Any = None
_backend: str = "memory"
_error: Optional[str] = None


def ensure_windows_selector_loop_policy() -> None:
    """psycopg async requires SelectorEventLoop on Windows (not Proactor)."""
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except Exception:
            pass


def to_psycopg_conninfo(database_url: str) -> str:
    """Convert SQLAlchemy async URL to a libpq/psycopg connection string."""
    url = (database_url or "").strip()
    for prefix in ("postgresql+asyncpg://", "postgres+asyncpg://", "postgresql+psycopg://"):
        if url.startswith(prefix):
            url = "postgresql://" + url[len(prefix) :]
            break
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


def checkpointer_status() -> dict:
    return {
        "backend": _backend,
        "durable": _backend == "postgres",
        "error": _error,
        "message": (
            "Checkpoints persist in Postgres across API restarts."
            if _backend == "postgres"
            else "In-memory checkpoints — Resume is lost if the API restarts."
        ),
    }


def get_active_checkpointer():
    return _checkpointer


async def _use_memory(reason: Optional[str] = None) -> dict:
    global _checkpointer, _backend, _error
    from langgraph.checkpoint.memory import MemorySaver

    _checkpointer = MemorySaver()
    _backend = "memory"
    _error = reason
    print(
        "[Checkpointer] Using MemorySaver"
        + (f" ({reason})" if reason else " (CHECKPOINT_BACKEND=memory)")
    )
    return checkpointer_status()


async def init_checkpointer() -> dict:
    """
    Prefer AsyncPostgresSaver when CHECKPOINT_BACKEND=postgres (default).
    Fall back to MemorySaver on failure so the API still boots.
    """
    global _pool, _checkpointer, _backend, _error

    ensure_windows_selector_loop_policy()
    settings = get_settings()
    wanted = (getattr(settings, "CHECKPOINT_BACKEND", None) or "postgres").strip().lower()

    if wanted in ("memory", "mem", "none"):
        return await _use_memory(None)

    try:
        from psycopg.rows import dict_row
        from psycopg_pool import AsyncConnectionPool
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        conninfo = to_psycopg_conninfo(settings.DATABASE_URL)
        _pool = AsyncConnectionPool(
            conninfo=conninfo,
            min_size=1,
            max_size=10,
            timeout=15.0,
            reconnect_timeout=5.0,
            kwargs={
                "autocommit": True,
                "prepare_threshold": 0,
                "row_factory": dict_row,
            },
            open=False,
        )
        await asyncio.wait_for(_pool.open(), timeout=20.0)
        saver = AsyncPostgresSaver(conn=_pool)
        await asyncio.wait_for(saver.setup(), timeout=30.0)
        _checkpointer = saver
        _backend = "postgres"
        _error = None
        print("[Checkpointer] AsyncPostgresSaver ready (durable)")
        return checkpointer_status()
    except Exception as exc:
        reason = f"{type(exc).__name__}: {exc}"
        print(f"[Checkpointer] Postgres failed ({reason}) — falling back to MemorySaver")
        if _pool is not None:
            try:
                await _pool.close()
            except Exception:
                pass
            _pool = None
        return await _use_memory(reason)


async def close_checkpointer() -> None:
    global _pool, _checkpointer, _backend
    if _pool is not None:
        try:
            await _pool.close()
        except Exception as exc:
            print(f"[Checkpointer] Pool close error: {exc}")
        _pool = None
    _checkpointer = None
    _backend = "memory"
