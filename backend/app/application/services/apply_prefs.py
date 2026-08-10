"""User apply preferences (Review vs Auto) + rate-limit counters — wiki entity."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import get_settings
from app.infrastructure.db.models import DBWikiEntity
from app.schemas.knowledge import WikiEntityCreate
from app.application.services.knowledge import KnowledgeBaseService

ENTITY_TYPE = "apply_prefs"
ENTITY_TITLE = "apply_preferences"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _day_key(dt: Optional[datetime] = None) -> str:
    return (dt or _utc_now()).strftime("%Y-%m-%d")


def _hour_key(dt: Optional[datetime] = None) -> str:
    return (dt or _utc_now()).strftime("%Y-%m-%d-%H")


class ApplyPrefsService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.kb = KnowledgeBaseService(db)
        self.settings = get_settings()

    def defaults(self) -> dict[str, Any]:
        return {
            "apply_mode": "review_and_apply",  # or auto_apply
            "auto_consent": False,
            "auto_consent_at": None,
            "max_per_hour": self.settings.AUTO_APPLY_MAX_PER_HOUR,
            "max_per_day": self.settings.AUTO_APPLY_MAX_PER_DAY,
            "min_confidence": self.settings.AUTO_APPLY_MIN_CONFIDENCE,
            "allowlist": self.settings.auto_apply_allowlist(),
            "blocklist": self.settings.auto_apply_blocklist(),
            "auto_enabled_globally": self.settings.AUTO_APPLY_ENABLED,
            "usage": {"day": _day_key(), "day_count": 0, "hour": _hour_key(), "hour_count": 0},
            "skip_queue": [],  # recent skip reasons for resume
        }

    async def _entity(self, user_id: UUID) -> Optional[DBWikiEntity]:
        result = await self.db.execute(
            select(DBWikiEntity).where(
                DBWikiEntity.user_id == user_id,
                DBWikiEntity.entity_type == ENTITY_TYPE,
                DBWikiEntity.title == ENTITY_TITLE,
            )
        )
        return result.scalars().first()

    async def get(self, user_id: UUID) -> dict[str, Any]:
        entity = await self._entity(user_id)
        base = self.defaults()
        if not entity:
            return base
        content = dict(entity.content or {})
        merged = {**base, **content}
        # Always refresh allow/block from server config (security)
        merged["allowlist"] = base["allowlist"]
        merged["blocklist"] = base["blocklist"]
        merged["auto_enabled_globally"] = base["auto_enabled_globally"]
        merged["usage"] = self._normalize_usage(merged.get("usage") or {})
        return merged

    def _normalize_usage(self, usage: dict[str, Any]) -> dict[str, Any]:
        day = _day_key()
        hour = _hour_key()
        out = {
            "day": day,
            "day_count": int(usage.get("day_count") or 0),
            "hour": hour,
            "hour_count": int(usage.get("hour_count") or 0),
        }
        if usage.get("day") != day:
            out["day_count"] = 0
        if usage.get("hour") != hour:
            out["hour_count"] = 0
        return out

    async def save(self, user_id: UUID, patch: dict[str, Any]) -> dict[str, Any]:
        current = await self.get(user_id)
        mode = patch.get("apply_mode", current.get("apply_mode"))
        if mode not in ("review_and_apply", "auto_apply"):
            mode = "review_and_apply"

        auto_consent = bool(patch.get("auto_consent", current.get("auto_consent")))
        if mode == "auto_apply" and self.settings.AUTO_APPLY_REQUIRE_CONSENT and not auto_consent:
            mode = "review_and_apply"

        if not self.settings.AUTO_APPLY_ENABLED:
            mode = "review_and_apply"
            auto_consent = False

        content = {
            **current,
            "apply_mode": mode,
            "auto_consent": auto_consent,
            "auto_consent_at": (
                _utc_now().isoformat()
                if auto_consent and not current.get("auto_consent")
                else current.get("auto_consent_at")
            ),
            "min_confidence": float(
                patch.get("min_confidence", current.get("min_confidence") or 0.72)
            ),
            "usage": self._normalize_usage(
                patch.get("usage") if "usage" in patch else (current.get("usage") or {})
            ),
            "skip_queue": list(
                patch.get("skip_queue")
                if "skip_queue" in patch
                else (current.get("skip_queue") or [])
            )[:40],
            "updated_at": _utc_now().isoformat(),
        }
        # Security lists always from config
        content["allowlist"] = self.settings.auto_apply_allowlist()
        content["blocklist"] = self.settings.auto_apply_blocklist()
        content["auto_enabled_globally"] = self.settings.AUTO_APPLY_ENABLED
        content["max_per_hour"] = self.settings.AUTO_APPLY_MAX_PER_HOUR
        content["max_per_day"] = self.settings.AUTO_APPLY_MAX_PER_DAY

        entity = await self._entity(user_id)
        if entity:
            entity.content = content
            await self.db.commit()
            await self.db.refresh(entity)
        else:
            await self.kb.create(
                user_id,
                WikiEntityCreate(
                    entity_type=ENTITY_TYPE,
                    title=ENTITY_TITLE,
                    content=content,
                ),
                index_vectors=False,
            )
        return content

    def host_allowed(self, prefs: dict[str, Any], host: str) -> tuple[bool, str]:
        h = (host or "").lower().split(":")[0]
        for blocked in prefs.get("blocklist") or []:
            b = blocked.replace("*.", "")
            if h == b or h.endswith("." + b) or b in h:
                return False, f"Host blocked (no aggressive LinkedIn automation): {h}"
        allow = prefs.get("allowlist") or []
        if not allow:
            return False, "Empty allowlist"
        for pattern in allow:
            p = pattern.lower().strip()
            if p.startswith("*."):
                suffix = p[1:]  # .myworkdayjobs.com
                if h.endswith(suffix) or h.endswith(p[2:]):
                    return True, "ok"
            elif h == p or h.endswith("." + p):
                return True, "ok"
        return False, f"Host not on Auto Apply allowlist: {h}"

    def rate_limit_ok(self, prefs: dict[str, Any]) -> tuple[bool, str]:
        usage = self._normalize_usage(prefs.get("usage") or {})
        max_h = int(prefs.get("max_per_hour") or self.settings.AUTO_APPLY_MAX_PER_HOUR)
        max_d = int(prefs.get("max_per_day") or self.settings.AUTO_APPLY_MAX_PER_DAY)
        if usage["hour_count"] >= max_h:
            return False, f"Hourly Auto Apply limit reached ({max_h}/hour)"
        if usage["day_count"] >= max_d:
            return False, f"Daily Auto Apply limit reached ({max_d}/day)"
        return True, "ok"

    async def record_submit(self, user_id: UUID) -> dict[str, Any]:
        prefs = await self.get(user_id)
        usage = self._normalize_usage(prefs.get("usage") or {})
        usage["hour_count"] = int(usage["hour_count"]) + 1
        usage["day_count"] = int(usage["day_count"]) + 1
        prefs["usage"] = usage
        return await self.save(user_id, prefs)

    async def push_skip(
        self,
        user_id: UUID,
        *,
        reason: str,
        host: str,
        url: Optional[str] = None,
        application_id: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> dict[str, Any]:
        prefs = await self.get(user_id)
        queue = list(prefs.get("skip_queue") or [])
        queue.insert(
            0,
            {
                "reason": reason,
                "host": host,
                "url": url,
                "application_id": application_id,
                "detail": detail,
                "at": _utc_now().isoformat(),
                "status": "paused",
            },
        )
        prefs["skip_queue"] = queue[:40]
        return await self.save(user_id, prefs)

    def can_auto_submit(self, prefs: dict[str, Any], *, host: str, confidence: float) -> dict[str, Any]:
        if not prefs.get("auto_enabled_globally"):
            return {"allowed": False, "reason": "Auto Apply disabled by server"}
        if prefs.get("apply_mode") != "auto_apply":
            return {"allowed": False, "reason": "Mode is Review & Apply (fill only)"}
        if self.settings.AUTO_APPLY_REQUIRE_CONSENT and not prefs.get("auto_consent"):
            return {"allowed": False, "reason": "Explicit Auto Apply consent required"}
        ok, reason = self.host_allowed(prefs, host)
        if not ok:
            return {"allowed": False, "reason": reason}
        ok, reason = self.rate_limit_ok(prefs)
        if not ok:
            return {"allowed": False, "reason": reason}
        min_c = float(prefs.get("min_confidence") or 0.72)
        if confidence < min_c:
            return {
                "allowed": False,
                "reason": f"Confidence {confidence:.2f} below threshold {min_c:.2f}",
            }
        return {"allowed": True, "reason": "ok", "min_confidence": min_c}
