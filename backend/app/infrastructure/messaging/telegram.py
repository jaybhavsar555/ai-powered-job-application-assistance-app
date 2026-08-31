"""Telegram Bot API — Loop Engineer packet alerts."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def telegram_configured() -> bool:
    token = (get_settings().TELEGRAM_BOT_TOKEN or "").strip()
    return bool(token)


async def get_bot_info() -> Optional[Dict[str, Any]]:
    token = (get_settings().TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            if resp.status_code != 200:
                return None
            data = resp.json()
            return data.get("result") if data.get("ok") else None
    except Exception as exc:
        logger.warning("Telegram getMe failed: %s", exc)
        return None


async def send_telegram_message(
    chat_id: str,
    text: str,
    *,
    parse_mode: Optional[str] = None,
) -> Dict[str, Any]:
    token = (get_settings().TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        return {"sent": False, "error": "TELEGRAM_BOT_TOKEN not configured"}
    if not (chat_id or "").strip():
        return {"sent": False, "error": "telegram_chat_id missing"}

    payload: Dict[str, Any] = {
        "chat_id": str(chat_id).strip(),
        "text": text[:4096],
        "disable_web_page_preview": False,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json=payload,
            )
            body = resp.json() if resp.content else {}
            if resp.status_code == 200 and body.get("ok"):
                return {"sent": True, "chat_id": chat_id}
            err = body.get("description") or resp.text[:200]
            return {"sent": False, "error": err}
    except Exception as exc:
        logger.warning("Telegram send failed: %s", exc)
        return {"sent": False, "error": str(exc)}


async def set_webhook(webhook_url: str) -> Dict[str, Any]:
    """Optional — call once in production to register Telegram webhook."""
    token = (get_settings().TELEGRAM_BOT_TOKEN or "").strip()
    if not token:
        return {"ok": False, "error": "no token"}
    secret = (get_settings().TELEGRAM_WEBHOOK_SECRET or "").strip()
    url = webhook_url
    if secret:
        url = f"{webhook_url}?secret={secret}"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                f"https://api.telegram.org/bot{token}/setWebhook",
                json={"url": url, "allowed_updates": ["message"]},
            )
            return resp.json()
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
