"""Web Push subscriptions for Loop Engineer (browser notifications)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _subs_path(user_id: UUID) -> Path:
    root = Path(getattr(get_settings(), "LOOP_ENGINEER_DIR", None) or "./data/loop_engineer")
    d = root / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d / "push_subscriptions.json"


def list_subscriptions(user_id: UUID) -> List[Dict[str, Any]]:
    path = _subs_path(user_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return list(data) if isinstance(data, list) else []
    except Exception:
        return []


def save_subscription(user_id: UUID, subscription: Dict[str, Any]) -> int:
    subs = list_subscriptions(user_id)
    endpoint = (subscription.get("endpoint") or "").strip()
    if not endpoint:
        return len(subs)
    subs = [s for s in subs if (s.get("endpoint") or "") != endpoint]
    subs.append(subscription)
    _subs_path(user_id).write_text(json.dumps(subs, indent=2), encoding="utf-8")
    return len(subs)


def remove_subscription(user_id: UUID, endpoint: str) -> int:
    subs = [s for s in list_subscriptions(user_id) if (s.get("endpoint") or "") != endpoint]
    _subs_path(user_id).write_text(json.dumps(subs, indent=2), encoding="utf-8")
    return len(subs)


def push_configured() -> bool:
    s = get_settings()
    return bool(
        (getattr(s, "WEB_PUSH_VAPID_PUBLIC_KEY", None) or "").strip()
        and (getattr(s, "WEB_PUSH_VAPID_PRIVATE_KEY", None) or "").strip()
    )


def get_vapid_public_key() -> Optional[str]:
    key = (getattr(get_settings(), "WEB_PUSH_VAPID_PUBLIC_KEY", None) or "").strip()
    return key or None


async def send_push_to_user(
    user_id: UUID,
    *,
    title: str,
    body: str,
    url: Optional[str] = None,
) -> Dict[str, Any]:
    if not push_configured():
        return {"sent": False, "reason": "WEB_PUSH_VAPID keys not configured"}

    subs = list_subscriptions(user_id)
    if not subs:
        return {"sent": False, "reason": "no push subscriptions"}

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        return {"sent": False, "error": "pywebpush not installed"}

    settings = get_settings()
    vapid_claims = {
        "sub": (getattr(settings, "WEB_PUSH_VAPID_SUBJECT", None) or "mailto:admin@localhost"),
    }
    payload = json.dumps(
        {
            "title": title[:120],
            "body": body[:500],
            "url": url or "/loop",
        }
    )
    sent = 0
    errors: List[str] = []
    stale: List[str] = []

    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=settings.WEB_PUSH_VAPID_PRIVATE_KEY,
                vapid_claims=vapid_claims,
            )
            sent += 1
        except WebPushException as exc:
            err = str(exc)
            errors.append(err[:120])
            if getattr(exc, "response", None) and exc.response.status_code in (404, 410):
                stale.append(sub.get("endpoint") or "")
        except Exception as exc:
            errors.append(str(exc)[:120])

    for ep in stale:
        if ep:
            remove_subscription(user_id, ep)

    return {
        "sent": sent > 0,
        "delivered": sent,
        "total_subscriptions": len(subs),
        "errors": errors[:3] if errors else None,
    }
