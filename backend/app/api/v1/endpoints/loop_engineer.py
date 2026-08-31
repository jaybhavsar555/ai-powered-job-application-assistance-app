"""Loop Engineer API — watchlist, schedule, and on-demand scans."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, get_db
from app.application.services.loop_engineer import LoopEngineerService
from app.domain.models import User

router = APIRouter()


class WatchCompanyBody(BaseModel):
    name: str
    careers_url: str = ""
    ats_host: str = ""
    priority: str = "normal"
    notes: str = ""


class SchedulePatch(BaseModel):
    enabled: Optional[bool] = None
    interval_hours: Optional[int] = Field(default=None, ge=1, le=168)
    watchlist_only: Optional[bool] = None
    resume_refresh_hint: Optional[bool] = None
    auto_build_packets: Optional[bool] = None
    notify_email: Optional[bool] = None
    notify_telegram: Optional[bool] = None
    notify_whatsapp: Optional[bool] = None
    notify_push: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    sync_portfolio_on_confirm: Optional[bool] = None
    auto_package_on_confirm: Optional[bool] = None
    preferences: Optional[Dict[str, Any]] = None


class NotifyTestBody(BaseModel):
    channel: str = Field(..., description="email | telegram | whatsapp | push")


class ConfirmPacketBody(BaseModel):
    start_apply: bool = True
    generate_package: Optional[bool] = None
    sync_portfolio: Optional[bool] = None


class BatchPacketBody(BaseModel):
    packet_ids: List[str] = Field(default_factory=list)
    start_apply: bool = True


class PushSubscribeBody(BaseModel):
    subscription: Dict[str, Any]


@router.get("/status")
async def loop_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    return await svc.status(current_user.id)


@router.get("/watchlist")
async def get_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    return {"watchlist": await svc.list_watchlist(current_user.id)}


@router.post("/watchlist")
async def add_watchlist_company(
    body: WatchCompanyBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    company = await svc.add_watch_company(
        current_user.id,
        name=body.name,
        careers_url=body.careers_url,
        ats_host=body.ats_host,
        priority=body.priority,
        notes=body.notes,
    )
    await db.commit()
    return {"company": company}


@router.delete("/watchlist/{entity_id}")
async def remove_watchlist_company(
    entity_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    return await svc.remove_watch_company(current_user.id, entity_id)


@router.post("/watchlist/seed-examples")
async def seed_watchlist_examples(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    result = await svc.seed_example_watchlist(current_user.id)
    await db.commit()
    return result


@router.get("/schedule")
async def get_schedule(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    return {"schedule": svc.get_schedule(current_user.id)}


@router.put("/schedule")
async def update_schedule(
    body: SchedulePatch,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    patch = body.model_dump(exclude_unset=True)
    return {"schedule": svc.save_schedule(current_user.id, patch)}


@router.post("/run-now")
async def run_now(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger an immediate Loop Engineer scan (Ollama/Kimi/DeepSeek via runtime LLM)."""
    svc = LoopEngineerService(db)
    return await svc.run_scan(current_user.id, trigger="manual")


@router.get("/digest")
async def loop_digest(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = LoopEngineerService(db)
    return {"lines": svc.digest_lines(current_user.id)}


@router.get("/packets")
async def list_packets(
    status: Optional[str] = None,
    run_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.application.services.job_packet import JobPacketService

    svc = JobPacketService(db)
    return {"packets": svc.list_packets(current_user.id, status=status, run_id=run_id)}


@router.get("/packets/{packet_id}")
async def get_packet(
    packet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.application.services.job_packet import JobPacketService

    svc = JobPacketService(db)
    return svc.get_packet(current_user.id, packet_id)


@router.post("/packets/{packet_id}/confirm")
async def confirm_packet(
    packet_id: str,
    body: ConfirmPacketBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """User approved research + resume preview → ingest job and start Review & Apply."""
    from app.application.services.job_packet import JobPacketService

    svc = JobPacketService(db)
    return await svc.confirm_packet(
        current_user.id,
        packet_id,
        start_apply=body.start_apply,
        generate_package=body.generate_package,
        sync_portfolio=body.sync_portfolio,
    )


@router.post("/packets/{packet_id}/reject")
async def reject_packet(
    packet_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.application.services.job_packet import JobPacketService

    svc = JobPacketService(db)
    return svc.reject_packet(current_user.id, packet_id)


@router.post("/packets/batch-confirm")
async def batch_confirm_packets(
    body: BatchPacketBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.application.services.job_packet import JobPacketService

    svc = JobPacketService(db)
    return await svc.batch_confirm(
        current_user.id, body.packet_ids, start_apply=body.start_apply
    )


@router.post("/packets/batch-reject")
async def batch_reject_packets(
    body: BatchPacketBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.application.services.job_packet import JobPacketService

    svc = JobPacketService(db)
    return svc.batch_reject(current_user.id, body.packet_ids)


@router.get("/portfolio/status")
async def portfolio_status(
    current_user: User = Depends(get_current_user),
):
    from app.application.services.portfolio_export import PortfolioExportService

    return PortfolioExportService().get_export_paths(current_user.id)


@router.get("/portfolio/preview")
async def portfolio_preview(
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import HTMLResponse
    from app.application.services.portfolio_export import PortfolioExportService

    html = PortfolioExportService().read_html(current_user.id)
    if not html:
        raise HTTPException(status_code=404, detail="No portfolio export yet — confirm a packet first.")
    return HTMLResponse(content=html)


@router.post("/portfolio/export-latest")
async def portfolio_export_latest(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-export portfolio from the most recent confirmed packet."""
    from app.application.services.job_packet import JobPacketService
    from app.application.services.portfolio_export import PortfolioExportService

    pkt_svc = JobPacketService(db)
    packets = pkt_svc.list_packets(current_user.id, limit=50)
    confirmed = next((p for p in packets if p.get("status") == "confirmed"), None)
    if not confirmed:
        raise HTTPException(status_code=404, detail="No confirmed packet to export from.")
    full = pkt_svc.get_packet(current_user.id, str(confirmed["id"]))
    email = await pkt_svc.get_user_email(current_user.id)
    return PortfolioExportService().export_from_packet(
        current_user.id, full, user_email=email
    )


@router.get("/notify/push/vapid-public-key")
async def push_vapid_public_key():
    from app.infrastructure.messaging.web_push import get_vapid_public_key, push_configured

    key = get_vapid_public_key()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="WEB_PUSH_VAPID_PUBLIC_KEY not set. Run: python scripts/generate_vapid_keys.py",
        )
    return {"publicKey": key, "configured": push_configured()}


@router.post("/notify/push/subscribe")
async def push_subscribe(
    body: PushSubscribeBody,
    current_user: User = Depends(get_current_user),
):
    from app.infrastructure.messaging.web_push import save_subscription

    count = save_subscription(current_user.id, body.subscription)
    return {"subscribed": True, "subscription_count": count}


@router.post("/notify/push/unsubscribe")
async def push_unsubscribe(
    body: Dict[str, Any],
    current_user: User = Depends(get_current_user),
):
    from app.infrastructure.messaging.web_push import remove_subscription

    endpoint = str(body.get("endpoint") or "")
    count = remove_subscription(current_user.id, endpoint)
    return {"unsubscribed": True, "subscription_count": count}


@router.post("/packets/build-for-run/{run_id}")
async def build_packets_for_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually build research packets for an existing pipeline run."""
    from app.application.services.search_pipeline import SearchPipelineService
    from app.application.services.job_packet import JobPacketService
    from app.application.services.loop_notify import LoopNotifyService

    pipeline = SearchPipelineService(db)
    run = pipeline.get_run(current_user.id, run_id)
    pkt_svc = JobPacketService(db)
    built = await pkt_svc.build_packets_for_run(current_user.id, run)
    loop_svc = LoopEngineerService(db)
    notify = await LoopNotifyService(db).notify_packets_ready(
        current_user.id,
        run_id=run_id,
        schedule=loop_svc.get_schedule(current_user.id),
    )
    return {"packets": built, "notify": notify}


@router.get("/notify/channels")
async def notify_channels(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.application.services.loop_notify import LoopNotifyService
    from app.infrastructure.messaging.telegram import get_bot_info, telegram_configured

    loop_svc = LoopEngineerService(db)
    schedule = loop_svc.get_schedule(current_user.id)
    notify = LoopNotifyService(db)
    bot = await get_bot_info() if telegram_configured() else None
    return {
        "channels": notify.channel_status(schedule),
        "telegram_bot": bot,
        "schedule": {
            "notify_email": schedule.get("notify_email"),
            "notify_telegram": schedule.get("notify_telegram"),
            "notify_whatsapp": schedule.get("notify_whatsapp"),
            "telegram_chat_id": schedule.get("telegram_chat_id") or "",
            "whatsapp_phone": schedule.get("whatsapp_phone") or "",
        },
    }


@router.post("/notify/telegram/link-code")
async def telegram_link_code(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a one-time code — send `/link CODE` to your Career OS Telegram bot."""
    from app.infrastructure.messaging.telegram_link import create_link_code
    from app.infrastructure.messaging.telegram import get_bot_info, telegram_configured

    if not telegram_configured():
        raise HTTPException(
            status_code=503,
            detail="TELEGRAM_BOT_TOKEN not set on server. Add it to backend/.env",
        )
    code = create_link_code(current_user.id)
    bot = await get_bot_info()
    username = (bot or {}).get("username") or "YourBot"
    return {
        "code": code,
        "expires_minutes": 60,
        "instructions": (
            f"1. Open Telegram and search @{username}\n"
            f"2. Send: /link {code}\n"
            "3. Your chat will be linked for packet alerts."
        ),
        "bot_username": username,
        "bot_url": f"https://t.me/{username}",
    }


@router.post("/notify/telegram/webhook")
async def telegram_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Telegram bot webhook — handles /link CODE to save chat_id.
    Register in production: setWebhook → /api/v1/loop-engineer/notify/telegram/webhook
    """
    from app.core.config import get_settings
    from app.infrastructure.messaging.telegram_link import consume_link_code
    from app.infrastructure.messaging.telegram import send_telegram_message

    settings = get_settings()
    secret = (settings.TELEGRAM_WEBHOOK_SECRET or "").strip()
    if secret and request.query_params.get("secret") != secret:
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    try:
        update = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    message = (update.get("message") or {})
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id") or "")
    text = (message.get("text") or "").strip()

    if not chat_id or not text:
        return {"ok": True}

    if text.lower().startswith("/start"):
        await send_telegram_message(
            chat_id,
            "Career OS Loop Engineer bot.\n\n"
            "Get a link code from /loop in Career OS, then send:\n"
            "/link YOUR_CODE",
        )
        return {"ok": True}

    if text.lower().startswith("/link"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await send_telegram_message(chat_id, "Usage: /link ABCD1234")
            return {"ok": True}
        code = parts[1].strip().upper()
        user_id = consume_link_code(code)
        if not user_id:
            await send_telegram_message(
                chat_id, "Invalid or expired code. Generate a new one in Career OS /loop."
            )
            return {"ok": True}

        from uuid import UUID

        loop_svc = LoopEngineerService(db)
        loop_svc.save_schedule(
            UUID(user_id),
            {
                "telegram_chat_id": chat_id,
                "notify_telegram": True,
            },
        )
        await send_telegram_message(
            chat_id,
            "Linked! You will receive job packet alerts here when Loop Engineer scans.",
        )
        return {"ok": True, "linked_user_id": user_id}

    return {"ok": True}


@router.post("/notify/test")
async def notify_test(
    body: NotifyTestBody,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from app.application.services.loop_notify import LoopNotifyService

    loop_svc = LoopEngineerService(db)
    schedule = loop_svc.get_schedule(current_user.id)
    result = await LoopNotifyService(db).send_test(
        current_user.id, schedule, channel=body.channel.strip().lower()
    )
    if not result.get("sent"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error") or result.get("reason") or "Test send failed",
        )
    return result
