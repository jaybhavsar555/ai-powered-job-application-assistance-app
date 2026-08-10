"""Gated Auto Apply control plane — consent, allowlist, rate limits, skip queue."""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified
import copy

from app.infrastructure.db.models import DBApplication, DBJob
from app.application.services.apply_prefs import ApplyPrefsService

logger = logging.getLogger(__name__)

SKIP_REASONS = frozenset(
    {"captcha", "login", "missing_answer", "low_confidence", "rate_limited", "blocked_host", "other"}
)


class AutoApplyBot:
    """
    Phase C control plane for Chrome extension Auto mode.

    Does NOT drive headless browsers from the server.
    Extension reports fill/submit/skip; we enforce consent, allowlist, rate limits,
    and map blockers → Needs input / Failed / Reapply.
    """

    STUB = False

    def __init__(self, db: AsyncSession):
        self.db = db
        self.prefs = ApplyPrefsService(db)

    async def evaluate(
        self,
        user_id: UUID,
        *,
        host: str,
        confidence: float,
    ) -> dict[str, Any]:
        prefs = await self.prefs.get(user_id)
        gate = self.prefs.can_auto_submit(prefs, host=host, confidence=confidence)
        return {
            "mode": prefs.get("apply_mode"),
            "gate": gate,
            "prefs": {
                "apply_mode": prefs.get("apply_mode"),
                "auto_consent": prefs.get("auto_consent"),
                "min_confidence": prefs.get("min_confidence"),
                "max_per_hour": prefs.get("max_per_hour"),
                "max_per_day": prefs.get("max_per_day"),
                "usage": prefs.get("usage"),
                "allowlist": prefs.get("allowlist"),
                "blocklist": prefs.get("blocklist"),
            },
        }

    async def handle_event(
        self,
        user_id: UUID,
        *,
        event_type: str,
        host: str,
        url: Optional[str] = None,
        application_id: Optional[str] = None,
        confidence: float = 0.0,
        reason: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> dict[str, Any]:
        event_type = (event_type or "").lower().strip()
        prefs = await self.prefs.get(user_id)

        if event_type == "evaluate":
            return await self.evaluate(user_id, host=host, confidence=confidence)

        if event_type == "filled":
            return {"ok": True, "event": "filled", "mode": prefs.get("apply_mode")}

        if event_type == "submit_attempt":
            gate = self.prefs.can_auto_submit(prefs, host=host, confidence=confidence)
            if not gate["allowed"]:
                await self.prefs.push_skip(
                    user_id,
                    reason="low_confidence" if "Confidence" in gate["reason"] else "other",
                    host=host,
                    url=url,
                    application_id=application_id,
                    detail=gate["reason"],
                )
                return {"ok": False, "allowed": False, "reason": gate["reason"]}
            return {"ok": True, "allowed": True, "reason": "ok"}

        if event_type == "submitted":
            gate = self.prefs.can_auto_submit(prefs, host=host, confidence=max(confidence, 0.99))
            # After user/extension already clicked, still enforce rate limit bookkeeping
            ok, reason_rl = self.prefs.rate_limit_ok(prefs)
            host_ok, host_reason = self.prefs.host_allowed(prefs, host)
            if not host_ok:
                return {"ok": False, "reason": host_reason}
            if not ok:
                return {"ok": False, "reason": reason_rl}
            await self.prefs.record_submit(user_id)
            stage_result = None
            if application_id:
                stage_result = await self._set_stage(
                    user_id, application_id, "Applied", note="Extension Auto Apply submitted"
                )
            return {
                "ok": True,
                "event": "submitted",
                "stage": stage_result,
                "gate": gate,
            }

        if event_type == "skip":
            skip_reason = (reason or "other").lower()
            if skip_reason not in SKIP_REASONS:
                skip_reason = "other"
            await self.prefs.push_skip(
                user_id,
                reason=skip_reason,
                host=host,
                url=url,
                application_id=application_id,
                detail=detail,
            )
            stage = "Needs input" if skip_reason in ("captcha", "login", "missing_answer") else "Failed"
            stage_result = None
            if application_id:
                stage_result = await self._set_stage(
                    user_id,
                    application_id,
                    stage,
                    note=f"Auto Apply paused: {skip_reason}"
                    + (f" — {detail}" if detail else ""),
                )
            return {
                "ok": True,
                "event": "skip",
                "stage": stage,
                "stage_result": stage_result,
                "resume_hint": "Fix blocker, move to Reapply on Tracker, then Start Applying again.",
            }

        if event_type == "reapply":
            if not application_id:
                raise HTTPException(status_code=400, detail="application_id required for reapply")
            stage_result = await self._set_stage(
                user_id, application_id, "Reapply", note="Queued for reapply after skip"
            )
            return {"ok": True, "event": "reapply", "stage_result": stage_result}

        raise HTTPException(status_code=400, detail=f"Unknown event_type: {event_type}")

    async def _set_stage(
        self,
        user_id: UUID,
        application_id: str,
        stage: str,
        *,
        note: str,
    ) -> Optional[dict[str, Any]]:
        try:
            aid = UUID(str(application_id))
        except (ValueError, TypeError):
            return None
        result = await self.db.execute(
            select(DBApplication)
            .where(DBApplication.id == aid, DBApplication.user_id == user_id)
            .options(selectinload(DBApplication.job).selectinload(DBJob.company))
        )
        app = result.scalars().first()
        if not app:
            return None
        app.stage = stage
        state = copy.deepcopy(dict(app.workflow_state or {}))
        state["auto_apply_last"] = {"stage": stage, "note": note}
        app.workflow_state = state
        flag_modified(app, "workflow_state")
        await self.db.commit()
        return {"application_id": str(app.id), "stage": stage, "note": note}

    async def apply(self, job_url: str, user_data: dict, resume_path: str):
        """Server-side apply remains disabled — extension is the apply engine."""
        logger.info("AutoApplyBot.apply refused for server-side URL %s", job_url)
        return {
            "success": False,
            "stub": False,
            "error": (
                "Server-side auto-apply is not used. Enable Auto mode in Inbox, "
                "consent, then use the Chrome extension on allowlisted ATS hosts."
            ),
        }
