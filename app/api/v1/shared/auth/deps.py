from typing import Any, Dict, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.api.v1.shared.auth.jwt import verify_token
from app.api.v1.shared.db.deps import get_db_session
from app.api.v1.shared.db.models import User
from app.core.logging import logger

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from JWT token.
    
    Verifies the token and checks that user exists in database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials

    # Verify JWT token
    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    # Convert string to UUID
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise credentials_exception

    # Verify user exists in DB (token revocation check)
    user = db.query(User).filter(
        User.id == user_uuid,
        User.is_active == True
    ).first()

    if not user:
        raise credentials_exception

    return {
        "sub": str(user.id),
        "email": user.email,
        "user_id": str(user.id),
        "created_at": user.created_at.isoformat() if user.created_at else "",
    }


def get_api_key_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Dependency for API key based authentication.
    
    API keys are still handled locally, separate from user auth.
    """
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
    return get_current_user(credentials, db)


def get_optional_user(
    authorization: Optional[str] = None,
    db: Session = Depends(get_db_session),
) -> Optional[Dict[str, Any]]:
    """
    Optional authentication - returns user if token is valid, None otherwise.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.replace("Bearer ", "")

    try:
        payload = verify_token(token)
        if payload:
            user_id = payload.get("sub")
            if user_id:
                try:
                    user_uuid = UUID(user_id)
                    user = db.query(User).filter(User.id == user_uuid, User.is_active == True).first()
                    if user:
                        return {
                            "sub": str(user.id),
                            "email": user.email,
                            "user_id": str(user.id),
                        }
                except ValueError:
                    pass
    except Exception:
        pass

    return None
