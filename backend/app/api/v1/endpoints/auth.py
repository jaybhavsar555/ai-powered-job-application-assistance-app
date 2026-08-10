from datetime import timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import get_settings
from app.core.security import create_access_token, get_password_hash, verify_password
from app.api.dependencies import get_db, get_current_user
from app.infrastructure.db.models import DBUser
from app.domain.models import User
from app.application.services.auth_seed import DEMO_USER_ID, SEED_ACCOUNTS, seed_phase12_users

router = APIRouter()

DEMO_EMAIL = "demo@example.com"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    role: str = "user"


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class MeResponse(BaseModel):
    id: str
    email: str
    auth_provider: str
    role: str


class SeedCredential(BaseModel):
    role: str
    email: str
    password: str


class CredentialsResponse(BaseModel):
    note: str
    accounts: list[SeedCredential]


async def ensure_demo_user(db: AsyncSession) -> DBUser:
    await seed_phase12_users(db)
    result = await db.execute(select(DBUser).where(DBUser.id == DEMO_USER_ID))
    user = result.scalars().first()
    if not user:
        result = await db.execute(select(DBUser).where(DBUser.email == DEMO_EMAIL))
        user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=500, detail="Demo user could not be created")
    return user


def _token_for(user: DBUser) -> TokenResponse:
    settings = get_settings()
    token = create_access_token(
        subject=str(user.id),
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return TokenResponse(
        access_token=token,
        user_id=str(user.id),
        email=user.email,
        role=getattr(user, "role", None) or "user",
    )


@router.get("/credentials", response_model=CredentialsResponse)
async def list_dev_credentials():
    """Dev helper — seeded Phase 12 accounts (not for production)."""
    settings = get_settings()
    if not settings.demo_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dev credentials are disabled outside development",
        )
    return CredentialsResponse(
        note="Local seed accounts created on API startup. Register also creates role=user.",
        accounts=[
            SeedCredential(role=a["role"], email=a["email"], password=a["password"])
            for a in SEED_ACCOUNTS
        ],
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)):
    email = data.email.lower().strip()
    existing = await db.execute(select(DBUser).where(DBUser.email == email))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = DBUser(
        email=email,
        auth_provider="local",
        hashed_password=get_password_hash(data.password),
        role="user",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return _token_for(user)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    if settings.seed_dev_users_enabled:
        await seed_phase12_users(db)
    email = data.email.lower().strip()
    result = await db.execute(select(DBUser).where(DBUser.email == email))
    user = result.scalars().first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return _token_for(user)


@router.get("/me", response_model=MeResponse)
async def me(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DBUser).where(DBUser.id == current_user.id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return MeResponse(
        id=str(user.id),
        email=user.email,
        auth_provider=user.auth_provider or "local",
        role=getattr(user, "role", None) or "user",
    )


@router.post("/demo", response_model=TokenResponse)
async def demo_login(db: AsyncSession = Depends(get_db)):
    """Issue a JWT for local development and ensure seed users exist."""
    settings = get_settings()
    if not settings.demo_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo login is disabled outside development",
        )
    user = await ensure_demo_user(db)
    return _token_for(user)


@router.get("/demo", response_model=TokenResponse)
async def demo_login_get(db: AsyncSession = Depends(get_db)):
    return await demo_login(db)
