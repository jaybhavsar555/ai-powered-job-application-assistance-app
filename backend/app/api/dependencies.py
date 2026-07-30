from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
from pydantic import ValidationError

from app.core.config import get_settings
from app.infrastructure.db.session import get_db
from app.domain.models import User
# Note: In a full implementation, we'd query the DB for the user here.

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> User:
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
    except (JWTError, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    # Placeholder for actual DB query
    # user = await db.get(DBUser, user_id)
    # if not user:
    #     raise HTTPException(status_code=404, detail="User not found")
    
    # Mock returning a user for skeleton purposes
    from uuid import UUID
    return User(id=UUID(user_id), email="skeleton@example.com", auth_provider="local")
