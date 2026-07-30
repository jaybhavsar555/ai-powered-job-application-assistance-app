from datetime import datetime, timedelta
from typing import Any, Optional, Union
import hashlib
import hmac
from jose import jwt
from app.core.config import get_settings

settings = get_settings()


def create_access_token(
    subject: Union[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_password_hash(password: str) -> str:
    """
    SHA-256 salted hash (prefixed). Avoids passlib/bcrypt breakage on newer Python builds.
    Format: sha256$<hex>
    """
    digest = hashlib.sha256(f"{settings.SECRET_KEY}:{password}".encode("utf-8")).hexdigest()
    return f"sha256${digest}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    if hashed_password.startswith("sha256$"):
        expected = get_password_hash(plain_password)
        return hmac.compare_digest(expected, hashed_password)
    # Legacy bcrypt via passlib if present
    try:
        from passlib.context import CryptContext

        return CryptContext(schemes=["bcrypt"], deprecated="auto").verify(
            plain_password, hashed_password
        )
    except Exception:
        return False
