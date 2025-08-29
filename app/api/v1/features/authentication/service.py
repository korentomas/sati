import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from app.api.v1.features.authentication.dto import (ApiKeyRequest,
                                                    ApiKeyResponse,
                                                    LoginRequest,
                                                    TokenResponse, UserProfile)
from app.api.v1.shared.auth.jwt import create_access_token, verify_password
from app.core.config import settings


class AuthService:
    """Authentication service with mock data."""

    # Mock user database
    _users = {
        "email@example.com": {
            "user_id": "user-123",
            "email": "email@example.com",
            "password_hash": "$2b$12$LmZpXjXDovKvDXXYrRhyB./IO0d31HxjdXm8thlVVsbEvE2AbF01C",  # "secret"
            "created_at": "2024-01-01T00:00:00Z",
        }
    }

    # Mock API keys storage
    _api_keys = {}

    async def authenticate_user(
        self, login_request: LoginRequest
    ) -> Optional[TokenResponse]:
        """Authenticate user and return access token."""
        user = self._users.get(login_request.email)
        if not user:
            return None

        if not verify_password(login_request.password, user["password_hash"]):
            return None

        token_data = {"sub": user["user_id"], "email": user["email"]}
        access_token = create_access_token(token_data)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.access_token_expire_minutes * 60,
        )

    async def create_api_key(
        self, user_id: str, request: ApiKeyRequest
    ) -> ApiKeyResponse:
        """Generate a new API key for the user."""
        key_id = str(uuid.uuid4())
        api_key = f"sat_{secrets.token_urlsafe(32)}"

        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=365)  # API keys expire in 1 year

        key_data = {
            "key_id": key_id,
            "api_key": api_key,
            "name": request.name,
            "description": request.description,
            "user_id": user_id,
            "created_at": created_at.isoformat() + "Z",
            "expires_at": expires_at.isoformat() + "Z",
        }

        self._api_keys[key_id] = key_data

        return ApiKeyResponse(**key_data)

    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID."""
        for user_data in self._users.values():
            if user_data["user_id"] == user_id:
                return UserProfile(
                    user_id=user_data["user_id"],
                    email=user_data["email"],
                    created_at=user_data["created_at"],
                )
        return None

    async def list_api_keys(self, user_id: str) -> list[dict]:
        """List all API keys for a user."""
        user_keys = []
        for key_data in self._api_keys.values():
            if key_data["user_id"] == user_id:
                # Don't return the actual API key, only metadata
                key_info = key_data.copy()
                key_info.pop("api_key", None)
                user_keys.append(key_info)
        return user_keys
