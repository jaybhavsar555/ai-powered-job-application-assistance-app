from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID

from app.core.config import get_settings
from app.infrastructure.db.session import get_db  # re-exported for endpoint imports
from app.infrastructure.db.models import DBUser
from app.domain.models import User

__all__ = ["get_db", "get_current_user", "oauth2_scheme"]

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise credentials_exc
        uid = UUID(user_id)
    except (JWTError, ValueError, TypeError):
        raise credentials_exc

    result = await db.execute(select(DBUser).where(DBUser.id == uid))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(
        id=user.id,
        email=user.email,
        auth_provider=user.auth_provider or "local",
        role=getattr(user, "role", None) or "user",
    )
