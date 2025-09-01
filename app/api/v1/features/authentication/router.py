from typing import Any, Dict, List

from fastapi import APIRouter, Depends

from app.api.v1.features.authentication.dto import (
    ApiKeyRequest,
    ApiKeyResponse,
    LoginRequest,
    TokenResponse,
    UserProfile,
)
from app.api.v1.features.authentication.handler import AuthHandler
from app.api.v1.shared.auth.deps import get_current_user

router = APIRouter()
auth_handler = AuthHandler()


@router.post("/login", response_model=TokenResponse)
async def login(login_request: LoginRequest) -> TokenResponse:
    """Authenticate user and return access token.

    Use email@example.com with password 'secret' for testing.
    """
    return await auth_handler.login(login_request)


@router.get("/profile", response_model=UserProfile)
async def get_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> UserProfile:
    """Get current user profile."""
    return await auth_handler.get_profile(current_user)


@router.post("/api-keys", response_model=ApiKeyResponse)
async def create_api_key(
    request: ApiKeyRequest, current_user: Dict[str, Any] = Depends(get_current_user)
) -> ApiKeyResponse:
    """Generate a new API key for the authenticated user."""
    return await auth_handler.create_api_key(current_user, request)


@router.get("/api-keys")
async def list_api_keys(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[dict]:
    """List all API keys for the authenticated user."""
    return await auth_handler.list_api_keys(current_user)
