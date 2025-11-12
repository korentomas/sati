from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.features.authentication.dto import (
    ApiKeyRequest,
    ApiKeyResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserProfile,
)
from app.api.v1.features.authentication.handler import AuthHandler
from app.api.v1.shared.auth.deps import get_current_user
from app.api.v1.shared.db.deps import get_db_session
from app.core.logging import logger

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    """
    Login with email and password.

    Returns a JWT token for API access.
    """
    handler = AuthHandler(db)
    token_response = handler.login(request)
    if not token_response:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return token_response


@router.post("/register", response_model=TokenResponse)
def register(
    request: RegisterRequest,
    db: Session = Depends(get_db_session),
) -> TokenResponse:
    """
    Register a new user with password hashing.

    Returns a JWT token for API access.
    """
    handler = AuthHandler(db)
    try:
        token_response = handler.register(request)
        if not token_response:
            raise HTTPException(status_code=400, detail="Registration failed")
        return token_response
    except ValueError as e:
        if "already exists" in str(e).lower():
            raise HTTPException(status_code=400, detail="User already exists")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
def logout(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """
    Logout the current user.
    """
    # Logout is just logging, no DB needed
    logger.info(f"User logged out: {current_user.get('email')}")
    return {"message": "Logged out successfully"}


@router.get("/profile", response_model=UserProfile)
def get_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> UserProfile:
    """
    Get current user profile.

    Requires a valid JWT token.
    """
    handler = AuthHandler(db)
    return handler.get_profile(current_user)


@router.post("/api-keys", response_model=ApiKeyResponse)
def create_api_key(
    request: ApiKeyRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> ApiKeyResponse:
    """
    Generate a new API key for the authenticated user.

    API keys are for programmatic access to the backend API.
    """
    handler = AuthHandler(db)
    return handler.create_api_key(current_user, request)


@router.get("/api-keys")
def list_api_keys(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> List[dict]:
    """
    List all API keys for the authenticated user.

    Returns metadata only, not the actual keys.
    """
    handler = AuthHandler(db)
    return handler.list_api_keys(current_user)


@router.delete("/api-keys/{key_id}")
def delete_api_key(
    key_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: Session = Depends(get_db_session),
) -> Dict[str, str]:
    """Delete an API key."""
    handler = AuthHandler(db)
    success = handler.delete_api_key(current_user, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key deleted successfully"}


@router.get("/verify")
def verify_token(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Verify if the current token is valid.

    Used to check if the JWT is still valid.
    """
    return {
        "valid": True,
        "user_id": current_user["user_id"],
        "email": current_user["email"],
    }
