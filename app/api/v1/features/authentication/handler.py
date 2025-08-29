from typing import Any, Dict

from app.api.v1.features.authentication.dto import (ApiKeyRequest,
                                                    ApiKeyResponse,
                                                    LoginRequest,
                                                    TokenResponse, UserProfile)
from app.api.v1.features.authentication.errors import (
    api_key_creation_error, invalid_credentials_error, user_not_found_error)
from app.api.v1.features.authentication.service import AuthService


class AuthHandler:
    """Authentication handler for orchestrating service calls."""

    def __init__(self):
        self.auth_service = AuthService()

    async def login(self, login_request: LoginRequest) -> TokenResponse:
        """Handle user login."""
        token_response = await self.auth_service.authenticate_user(login_request)
        if not token_response:
            raise invalid_credentials_error()
        return token_response

    async def create_api_key(
        self, current_user: Dict[str, Any], request: ApiKeyRequest
    ) -> ApiKeyResponse:
        """Handle API key creation."""
        try:
            user_id = current_user["sub"]
            api_key_response = await self.auth_service.create_api_key(user_id, request)
            return api_key_response
        except Exception:
            raise api_key_creation_error()

    async def get_profile(self, current_user: Dict[str, Any]) -> UserProfile:
        """Handle user profile retrieval."""
        user_id = current_user["sub"]
        profile = await self.auth_service.get_user_profile(user_id)
        if not profile:
            raise user_not_found_error()
        return profile

    async def list_api_keys(self, current_user: Dict[str, Any]) -> list[dict]:
        """Handle listing user's API keys."""
        user_id = current_user["sub"]
        return await self.auth_service.list_api_keys(user_id)
