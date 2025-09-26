from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.v1.shared.auth.jwt import verify_token
from app.api.v1.shared.auth.supabase import supabase_auth
from app.core.logging import logger

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from Supabase JWT token.

    This verifies the token with Supabase and returns user information.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    # First try to verify with Supabase
    user = await supabase_auth.verify_token(token)
    if user:
        return {
            "sub": user.id,
            "email": user.email,
            "user_id": user.id,
            "created_at": user.created_at,
        }

    # Fallback to local JWT verification (for API keys)
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    return payload


async def get_api_key_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Dict[str, Any]:
    """
    Dependency for API key based authentication.

    API keys are still handled locally, separate from Supabase user auth.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    # Check if it's an API key (starts with 'sat_')
    if token.startswith("sat_"):
        # TODO: Implement API key validation from database
        # For now, return a mock user
        logger.info(f"API key authentication attempted: {token[:10]}...")
        return {
            "sub": "api-key-user",
            "email": "api@example.com",
            "is_api_key": True,
        }

    # Otherwise, use regular user authentication
    return await get_current_user(credentials)


async def get_optional_user(
    authorization: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - returns user if token is valid, None otherwise.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")

    try:
        user = await supabase_auth.verify_token(token)
        if user:
            return {
                "sub": user.id,
                "email": user.email,
                "user_id": user.id,
            }
    except Exception:
        pass

    return None
