"""WhatsApp notifications — Meta Cloud API or Twilio."""

from __future__ import annotations

import logging
from typing import Any, Dict

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    return "".join(c for c in (phone or "") if c.isdigit())


def whatsapp_configured() -> bool:
    settings = get_settings()
    provider = (getattr(settings, "WHATSAPP_PROVIDER", None) or "").strip().lower()
    if provider == "twilio":
        return bool(
            settings.TWILIO_ACCOUNT_SID
            and settings.TWILIO_AUTH_TOKEN
            and settings.TWILIO_WHATSAPP_FROM
        )
    if provider == "meta":
        return bool(
            settings.WHATSAPP_META_ACCESS_TOKEN
            and settings.WHATSAPP_META_PHONE_NUMBER_ID
        )
    return False


async def send_whatsapp_message(to_phone: str, text: str) -> Dict[str, Any]:
    settings = get_settings()
    provider = (getattr(settings, "WHATSAPP_PROVIDER", None) or "").strip().lower()
    to = _normalize_phone(to_phone)
    if not to:
        return {"sent": False, "error": "whatsapp_phone missing or invalid"}

    if provider == "twilio":
        return await _send_twilio(to, text, settings)
    if provider == "meta":
        return await _send_meta(to, text, settings)
    return {
        "sent": False,
        "error": "WHATSAPP_PROVIDER not set (use 'meta' or 'twilio')",
    }


async def _send_meta(to: str, text: str, settings: Any) -> Dict[str, Any]:
    token = (settings.WHATSAPP_META_ACCESS_TOKEN or "").strip()
    phone_id = (settings.WHATSAPP_META_PHONE_NUMBER_ID or "").strip()
    if not token or not phone_id:
        return {"sent": False, "error": "WhatsApp Meta credentials missing"}

    url = f"https://graph.facebook.com/v21.0/{phone_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"preview_url": True, "body": text[:4096]},
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {token}"},
                json=payload,
            )
            body = resp.json() if resp.content else {}
            if resp.status_code in (200, 201) and not body.get("error"):
                return {"sent": True, "to": to, "provider": "meta"}
            err = body.get("error", {}).get("message") or resp.text[:200]
            return {"sent": False, "error": err, "provider": "meta"}
    except Exception as exc:
        logger.warning("WhatsApp Meta send failed: %s", exc)
        return {"sent": False, "error": str(exc), "provider": "meta"}


async def _send_twilio(to: str, text: str, settings: Any) -> Dict[str, Any]:
    sid = (settings.TWILIO_ACCOUNT_SID or "").strip()
    token = (settings.TWILIO_AUTH_TOKEN or "").strip()
    from_num = (settings.TWILIO_WHATSAPP_FROM or "").strip()
    if not sid or not token or not from_num:
        return {"sent": False, "error": "Twilio WhatsApp credentials missing"}

    from_wa = from_num if from_num.startswith("whatsapp:") else f"whatsapp:{from_num}"
    to_wa = f"whatsapp:+{to}" if not to.startswith("+") else f"whatsapp:{to}"

    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(
                url,
                auth=(sid, token),
                data={"From": from_wa, "To": to_wa, "Body": text[:1600]},
            )
            if resp.status_code in (200, 201):
                return {"sent": True, "to": to, "provider": "twilio"}
            return {
                "sent": False,
                "error": resp.text[:200],
                "provider": "twilio",
            }
    except Exception as exc:
        logger.warning("Twilio WhatsApp send failed: %s", exc)
        return {"sent": False, "error": str(exc), "provider": "twilio"}
