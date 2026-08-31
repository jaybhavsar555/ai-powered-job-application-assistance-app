"""Loop Engineer notifications — email digest when job packets are ready."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.mail import MailService
from app.application.services.job_packet import JobPacketService
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class LoopNotifyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.mail = MailService()
        self.packets = JobPacketService(db)
        self.settings = get_settings()

    def _notify_enabled(self, schedule: Optional[Dict[str, Any]] = None) -> bool:
        if schedule and schedule.get("notify_email") is False:
            return False
        return bool(getattr(self.settings, "LOOP_ENGINEER_NOTIFY_EMAIL", True))

    async def notify_packets_ready(
        self,
        user_id: UUID,
        *,
        run_id: Optional[str] = None,
        schedule: Optional[Dict[str, Any]] = None,
        frontend_base: str = "http://localhost:3000",
    ) -> Dict[str, Any]:
        """
        Email user when new pending_review packets exist (once per batch).
        Falls back to inbox digest when SMTP not configured.
        """
        if not self._notify_enabled(schedule):
            return {"sent": False, "reason": "notify_email disabled"}

        pending = self.packets.list_packets(user_id, status="pending_review", run_id=run_id)
        unnotified = [p for p in pending if not p.get("notified_at")]
        if not unnotified:
            return {"sent": False, "reason": "no new packets"}

        to_email = await self.packets.get_user_email(user_id)
        if not to_email:
            return {"sent": False, "reason": "no user email"}

        lines = []
        for p in unnotified[:12]:
            score = p.get("match_score") or "?"
            lines.append(
                f"• {p.get('title')} @ {p.get('company')} (match {score}%)\n"
                f"  Review: {frontend_base}/loop?packet={p.get('id')}"
            )

        subject = (
            f"Career OS: {len(unnotified)} job packet(s) ready for your review"
        )
        body = (
            "Loop Engineer found roles and built research + resume previews.\n\n"
            "Nothing was applied — confirm each job in Loop Engineer when ready.\n\n"
            + "\n".join(lines)
            + f"\n\nOpen Loop Engineer: {frontend_base}/loop\n"
            + f"Pipeline run: {frontend_base}/pipeline"
            + (f"?run_id={run_id}" if run_id else "")
            + "\n"
        )

        sent = False
        error = None
        try:
            sent = self.mail.send_email(to_email, subject, body)
        except Exception as exc:
            error = str(exc)
            logger.warning("Loop notify email failed: %s", exc)

        if sent:
            self.packets.mark_notified(
                user_id, [str(p["id"]) for p in unnotified if p.get("id")]
            )

        return {
            "sent": sent,
            "to": to_email,
            "packet_count": len(unnotified),
            "smtp_configured": self.mail.smtp_configured,
            "error": error,
            "fallback": "Check Inbox digest and /loop if email did not arrive.",
        }
