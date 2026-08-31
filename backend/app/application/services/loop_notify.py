"""Loop Engineer notifications — email, Telegram, and WhatsApp."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.mail import MailService
from app.application.services.job_packet import JobPacketService
from app.core.config import get_settings
from app.infrastructure.messaging.telegram import send_telegram_message, telegram_configured
from app.infrastructure.messaging.whatsapp import send_whatsapp_message, whatsapp_configured
from app.infrastructure.messaging.web_push import (
    push_configured,
    send_push_to_user,
)

logger = logging.getLogger(__name__)


class LoopNotifyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mail = MailService()
        self.packets = JobPacketService(db)
        self.settings = get_settings()

    def channel_status(self, schedule: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        sched = schedule or {}
        return {
            "email": {
                "configured": self.mail.smtp_configured or not self.settings.is_production,
                "enabled": sched.get("notify_email", True),
            },
            "telegram": {
                "configured": telegram_configured(),
                "enabled": bool(sched.get("notify_telegram")),
                "chat_id_set": bool((sched.get("telegram_chat_id") or "").strip()),
            },
            "whatsapp": {
                "configured": whatsapp_configured(),
                "enabled": bool(sched.get("notify_whatsapp")),
                "phone_set": bool((sched.get("whatsapp_phone") or "").strip()),
                "provider": (getattr(self.settings, "WHATSAPP_PROVIDER", None) or "").strip()
                or None,
            },
            "push": {
                "configured": push_configured(),
                "enabled": sched.get("notify_push", True),
            },
        }

    def _build_message(
        self,
        unnotified: List[Dict[str, Any]],
        *,
        frontend_base: str,
        run_id: Optional[str],
    ) -> tuple[str, str]:
        lines = []
        for p in unnotified[:12]:
            score = p.get("match_score") or "?"
            lines.append(
                f"• {p.get('title')} @ {p.get('company')} (match {score}%)\n"
                f"  {frontend_base}/loop?packet={p.get('id')}"
            )

        subject = f"Career OS: {len(unnotified)} job packet(s) ready for review"
        body = (
            "Loop Engineer found roles and built research + resume previews.\n\n"
            "Nothing was applied — confirm each job in Loop Engineer when ready.\n\n"
            + "\n".join(lines)
            + f"\n\nOpen: {frontend_base}/loop\n"
        )
        if run_id:
            body += f"Pipeline: {frontend_base}/pipeline?run_id={run_id}\n"
        return subject, body

    async def _send_email(
        self,
        user_id: UUID,
        schedule: Dict[str, Any],
        subject: str,
        body: str,
    ) -> Dict[str, Any]:
        if schedule.get("notify_email") is False:
            return {"sent": False, "reason": "notify_email disabled"}
        if not bool(getattr(self.settings, "LOOP_ENGINEER_NOTIFY_EMAIL", True)):
            return {"sent": False, "reason": "LOOP_ENGINEER_NOTIFY_EMAIL=false"}

        to_email = await self.packets.get_user_email(user_id)
        if not to_email:
            return {"sent": False, "reason": "no user email"}

        try:
            sent = self.mail.send_email(to_email, subject, body)
            return {"sent": sent, "to": to_email}
        except Exception as exc:
            logger.warning("Loop notify email failed: %s", exc)
            return {"sent": False, "error": str(exc), "to": to_email}

    async def _send_telegram(
        self, schedule: Dict[str, Any], body: str
    ) -> Dict[str, Any]:
        if not schedule.get("notify_telegram"):
            return {"sent": False, "reason": "notify_telegram disabled"}
        chat_id = (schedule.get("telegram_chat_id") or "").strip()
        if not chat_id:
            return {"sent": False, "reason": "telegram_chat_id not set"}
        return await send_telegram_message(chat_id, body)

    async def _send_whatsapp(
        self, schedule: Dict[str, Any], body: str
    ) -> Dict[str, Any]:
        if not schedule.get("notify_whatsapp"):
            return {"sent": False, "reason": "notify_whatsapp disabled"}
        phone = (schedule.get("whatsapp_phone") or "").strip()
        if not phone:
            return {"sent": False, "reason": "whatsapp_phone not set"}
        return await send_whatsapp_message(phone, body)

    async def _send_push(
        self,
        user_id: UUID,
        schedule: Dict[str, Any],
        title: str,
        body: str,
        url: str,
    ) -> Dict[str, Any]:
        if schedule.get("notify_push") is False:
            return {"sent": False, "reason": "notify_push disabled"}
        return await send_push_to_user(user_id, title=title, body=body, url=url)

    async def notify_packets_ready(
        self,
        user_id: UUID,
        *,
        run_id: Optional[str] = None,
        schedule: Optional[Dict[str, Any]] = None,
        frontend_base: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Notify via all enabled channels when new packets exist."""
        schedule = schedule or {}
        base = frontend_base or getattr(
            self.settings, "LOOP_ENGINEER_FRONTEND_URL", "http://localhost:3000"
        )

        pending = self.packets.list_packets(user_id, status="pending_review", run_id=run_id)
        unnotified = [p for p in pending if not p.get("notified_at")]
        if not unnotified:
            return {"sent": False, "reason": "no new packets", "channels": {}}

        subject, body = self._build_message(unnotified, frontend_base=base, run_id=run_id)

        channels: Dict[str, Any] = {}
        channels["email"] = await self._send_email(user_id, schedule, subject, body)
        channels["telegram"] = await self._send_telegram(schedule, body)
        channels["whatsapp"] = await self._send_whatsapp(schedule, body)
        push_url = f"{base}/loop"
        if len(unnotified) == 1 and unnotified[0].get("id"):
            push_url = f"{base}/loop?packet={unnotified[0]['id']}"
        channels["push"] = await self._send_push(
            user_id,
            schedule,
            subject,
            f"{len(unnotified)} job packet(s) ready — tap to review.",
            push_url,
        )

        any_sent = any(ch.get("sent") for ch in channels.values())
        if any_sent:
            self.packets.mark_notified(
                user_id, [str(p["id"]) for p in unnotified if p.get("id")]
            )

        return {
            "sent": any_sent,
            "packet_count": len(unnotified),
            "channels": channels,
            "fallback": "Check Inbox digest and /loop if no message arrived.",
        }

    async def send_test(
        self,
        user_id: UUID,
        schedule: Dict[str, Any],
        *,
        channel: str,
    ) -> Dict[str, Any]:
        base = getattr(self.settings, "LOOP_ENGINEER_FRONTEND_URL", "http://localhost:3000")
        body = (
            "Career OS Loop Engineer test notification.\n\n"
            f"When job packets are ready you will get links like:\n{base}/loop\n"
        )
        if channel == "email":
            return await self._send_email(
                user_id,
                {**schedule, "notify_email": True},
                "Career OS — test notification",
                body,
            )
        if channel == "telegram":
            return await self._send_telegram({**schedule, "notify_telegram": True}, body)
        if channel == "whatsapp":
            return await self._send_whatsapp({**schedule, "notify_whatsapp": True}, body)
        if channel == "push":
            return await self._send_push(
                user_id,
                {**schedule, "notify_push": True},
                "Career OS — test",
                body,
                base + "/loop",
            )
        return {"sent": False, "error": f"unknown channel: {channel}"}
