from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException

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

router = APIRouter()
auth_handler = AuthHandler()


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest) -> TokenResponse:
    """
    Login with email and password.

    Backend handles Supabase authentication internally and returns
    a backend JWT token for API access.
    """
    token_response = await auth_handler.login(request)
    if not token_response:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return token_response


@router.post("/register", response_model=TokenResponse)
async def register(request: RegisterRequest) -> TokenResponse:
    """
    Register a new user.

    Backend creates user in Supabase and returns a backend JWT token.
    """
    token_response = await auth_handler.register(request)
    if not token_response:
        raise HTTPException(status_code=400, detail="Registration failed")
    return token_response


@router.post("/logout")
async def logout(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, str]:
    """
    Logout the current user.

    Backend handles Supabase logout internally.
    """
    await auth_handler.logout(current_user)
    return {"message": "Logged out successfully"}


@router.get("/profile", response_model=UserProfile)
async def get_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> UserProfile:
    """
    Get current user profile.

    Requires a valid backend JWT token.
    """
    return UserProfile(
        user_id=current_user["user_id"],
        email=current_user["email"],
        created_at=current_user.get("created_at", ""),
    )


@router.post("/api-keys", response_model=ApiKeyResponse)
async def create_api_key(
    request: ApiKeyRequest, current_user: Dict[str, Any] = Depends(get_current_user)
) -> ApiKeyResponse:
    """
    Generate a new API key for the authenticated user.

    API keys are for programmatic access to the backend API.
    """
    return await auth_handler.create_api_key(current_user, request)


@router.get("/api-keys")
async def list_api_keys(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> List[dict]:
    """
    List all API keys for the authenticated user.

    Returns metadata only, not the actual keys.
    """
    return await auth_handler.list_api_keys(current_user)


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, str]:
    """Delete an API key."""
    success = await auth_handler.delete_api_key(current_user, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key deleted successfully"}


@router.get("/verify")
async def verify_token(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Verify if the current token is valid.

    Used to check if the backend JWT is still valid.
    """
    return {
        "valid": True,
        "user_id": current_user["user_id"],
        "email": current_user["email"],
    }