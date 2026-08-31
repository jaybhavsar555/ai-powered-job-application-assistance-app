"""Extension apply queue — jobs confirmed via Loop Engineer, ready for autofill."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _queue_path(user_id: UUID) -> Path:
    root = Path(getattr(get_settings(), "LOOP_ENGINEER_DIR", None) or "./data/loop_engineer")
    d = root / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / "extension_apply_queue.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_queue(user_id: UUID, *, include_done: bool = False) -> List[Dict[str, Any]]:
    path = _queue_path(user_id)
    if not path.exists():
        return []
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(items, list):
            return []
        if include_done:
            return items
        return [i for i in items if i.get("status") != "done"]
    except Exception:
        return []


def enqueue(
    user_id: UUID,
    *,
    application_id: str,
    job_id: str,
    url: Optional[str],
    company: str,
    title: str,
    packet_id: Optional[str] = None,
    package_files: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    items = list_queue(user_id, include_done=True)
    entry = {
        "id": packet_id or application_id,
        "application_id": application_id,
        "job_id": job_id,
        "url": url,
        "company": company,
        "title": title,
        "packet_id": packet_id,
        "package_files": package_files or {},
        "status": "pending",
        "enqueued_at": _utc_now_iso(),
    }
    # Dedupe by application_id
    items = [i for i in items if i.get("application_id") != application_id]
    items.insert(0, entry)
    items = items[:30]
    _queue_path(user_id).write_text(json.dumps(items, indent=2), encoding="utf-8")
    return entry


def mark_done(user_id: UUID, application_id: str) -> bool:
    items = list_queue(user_id, include_done=True)
    found = False
    for i in items:
        if i.get("application_id") == application_id:
            i["status"] = "done"
            i["done_at"] = _utc_now_iso()
            found = True
    if found:
        _queue_path(user_id).write_text(json.dumps(items, indent=2), encoding="utf-8")
    return found
