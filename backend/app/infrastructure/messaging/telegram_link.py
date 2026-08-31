"""One-time codes to link Telegram chat_id to Career OS user."""

from __future__ import annotations

import json
import secrets
import string
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import UUID

from app.core.config import get_settings

_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _store_path() -> Path:
    root = Path(getattr(get_settings(), "LOOP_ENGINEER_DIR", None) or "./data/loop_engineer")
    root.mkdir(parents=True, exist_ok=True)
    return root / "telegram_link_codes.json"


def _load() -> Dict[str, Any]:
    path = _store_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save(data: Dict[str, Any]) -> None:
    _store_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def create_link_code(user_id: UUID, *, ttl_minutes: int = 60) -> str:
    data = _load()
    # Drop expired
    now = datetime.now(timezone.utc)
    data = {
        k: v
        for k, v in data.items()
        if datetime.fromisoformat(v["expires_at"].replace("Z", "+00:00")) > now
    }
    code = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
    data[code] = {
        "user_id": str(user_id),
        "expires_at": (now + timedelta(minutes=ttl_minutes)).isoformat(),
    }
    _save(data)
    return code


def consume_link_code(code: str) -> Optional[str]:
    data = _load()
    entry = data.get((code or "").strip().upper())
    if not entry:
        return None
    try:
        exp = datetime.fromisoformat(entry["expires_at"].replace("Z", "+00:00"))
        if exp < datetime.now(timezone.utc):
            data.pop(code, None)
            _save(data)
            return None
    except Exception:
        return None
    user_id = entry.get("user_id")
    data.pop(code, None)
    _save(data)
    return str(user_id) if user_id else None
