from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a new JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt: str = jwt.encode(
        to_encode, settings.secret_key, algorithm=settings.algorithm
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and decode a JWT token with better error handling."""
    try:
        payload: Dict[str, Any] = jwt.decode(
            token, settings.secret_key, algorithms=[settings.algorithm]
        )

        # Verify required fields
        if "sub" not in payload:
            return None

        return payload
    except JWTError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    # Convert string to bytes if needed
    plain_bytes: bytes = (
        plain_password.encode("utf-8")
        if isinstance(plain_password, str)
        else plain_password
    )
    hash_bytes: bytes = (
        hashed_password.encode("utf-8")
        if isinstance(hashed_password, str)
        else hashed_password
    )

    return bcrypt.checkpw(plain_bytes, hash_bytes)  # type: ignore[no-any-return]


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    # Convert string to bytes
    password_bytes: bytes = (
        password.encode("utf-8") if isinstance(password, str) else password
    )

    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")  # type: ignore[no-any-return]
