"""
Phase 12 — seed accounts + roles for local/dev.

| Role  | Email                       | Password  |
|-------|-----------------------------|-----------|
| admin | admin@example.com           | Admin123! |
| admin | jay.bhavsar.dev@gmail.com   | (kept if exists; else Admin123!) |
| demo  | demo@example.com            | Demo1234! |
| user  | user@example.com            | User1234! |
"""
from __future__ import annotations

from typing import List, TypedDict
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.security import get_password_hash
from app.infrastructure.db.models import DBUser
from app.infrastructure.db.session import async_session

DEMO_USER_ID = UUID("00000000-0000-4000-8000-000000000001")
ADMIN_USER_ID = UUID("00000000-0000-4000-8000-0000000000a1")
USER_USER_ID = UUID("00000000-0000-4000-8000-0000000000b1")
JAY_ADMIN_USER_ID = UUID("00000000-0000-4000-8000-0000000000c1")

# Always force these emails to role=admin on startup (password left alone if account exists)
PROMOTE_ADMIN_EMAILS = [
    "jay.bhavsar.dev@gmail.com",
]


class SeedAccount(TypedDict):
    id: UUID
    email: str
    password: str
    role: str
    auth_provider: str


SEED_ACCOUNTS: List[SeedAccount] = [
    {
        "id": ADMIN_USER_ID,
        "email": "admin@example.com",
        "password": "Admin123!",
        "role": "admin",
        "auth_provider": "local",
    },
    {
        "id": DEMO_USER_ID,
        "email": "demo@example.com",
        "password": "Demo1234!",
        "role": "demo",
        "auth_provider": "demo",
    },
    {
        "id": USER_USER_ID,
        "email": "user@example.com",
        "password": "User1234!",
        "role": "user",
        "auth_provider": "local",
    },
    {
        "id": JAY_ADMIN_USER_ID,
        "email": "jay.bhavsar.dev@gmail.com",
        "password": "Admin123!",
        "role": "admin",
        "auth_provider": "local",
    },
]


async def ensure_users_role_column(db: AsyncSession) -> None:
    await db.execute(
        text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR DEFAULT 'user'")
    )
    await db.commit()


async def _promote_admins(db: AsyncSession) -> List[str]:
    """Ensure listed emails are admin. Create with default password only if missing."""
    promoted: List[str] = []
    for email in PROMOTE_ADMIN_EMAILS:
        email_l = email.lower().strip()
        result = await db.execute(select(DBUser).where(DBUser.email == email_l))
        user = result.scalars().first()
        if user:
            if (user.role or "user") != "admin":
                user.role = "admin"
                promoted.append(f"{email_l} (promoted)")
            else:
                promoted.append(f"{email_l} (already admin)")
            continue
        seed = next((a for a in SEED_ACCOUNTS if a["email"].lower() == email_l), None)
        db.add(
            DBUser(
                id=seed["id"] if seed else uuid4(),
                email=email_l,
                hashed_password=get_password_hash(seed["password"] if seed else "Admin123!"),
                role="admin",
                auth_provider="local",
            )
        )
        promoted.append(f"{email_l} (created admin)")
    return promoted


async def seed_phase12_users(db: AsyncSession) -> None:
    await ensure_users_role_column(db)
    promote_set = {e.lower() for e in PROMOTE_ADMIN_EMAILS}
    for acct in SEED_ACCOUNTS:
        result = await db.execute(select(DBUser).where(DBUser.email == acct["email"]))
        user = result.scalars().first()
        password_hash = get_password_hash(acct["password"])
        # Don't overwrite password for personal admin emails that may already exist
        preserve_password = acct["email"].lower() in promote_set
        if user:
            if not preserve_password:
                user.hashed_password = password_hash
            user.role = acct["role"]
            user.auth_provider = acct["auth_provider"]
            continue
        by_id = await db.execute(select(DBUser).where(DBUser.id == acct["id"]))
        existing = by_id.scalars().first()
        if existing:
            existing.email = acct["email"]
            if not preserve_password:
                existing.hashed_password = password_hash
            existing.role = acct["role"]
            existing.auth_provider = acct["auth_provider"]
            continue
        db.add(
            DBUser(
                id=acct["id"],
                email=acct["email"],
                hashed_password=password_hash,
                role=acct["role"],
                auth_provider=acct["auth_provider"],
            )
        )
    await _promote_admins(db)
    await db.commit()


async def bootstrap_auth() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    if not settings.seed_dev_users_enabled:
        print("[Auth] Dev user seed skipped (production / SEED_DEV_USERS=false)")
        return

    async with async_session() as db:
        try:
            await seed_phase12_users(db)
            print(
                "[Auth] Seeded roles — "
                "admin@example.com / Admin123! · "
                "jay.bhavsar.dev@gmail.com (admin) · "
                "demo@example.com / Demo1234! · "
                "user@example.com / User1234!"
            )
        except Exception as exc:
            print(f"[Auth] Seed skipped: {exc}")
