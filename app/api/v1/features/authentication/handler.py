from typing import Any, Dict, List, Optional

from app.api.v1.features.authentication.dto import (
    ApiKeyRequest,
    ApiKeyResponse,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserProfile,
)
from app.api.v1.features.authentication.errors import (
    api_key_creation_error,
    user_not_found_error,
)
from app.api.v1.features.authentication.service import AuthService
from app.api.v1.shared.auth.jwt import create_access_token
from app.api.v1.shared.auth.supabase import supabase_auth
from app.core.config import settings
from app.core.logging import logger


class AuthHandler:
    """Authentication handler for orchestrating service calls."""

    def __init__(self) -> None:
        self.auth_service = AuthService()

    async def login(self, login_request: LoginRequest) -> Optional[TokenResponse]:
        """Handle user login using Supabase."""
        try:
            # Authenticate with Supabase
            response = supabase_auth.client.auth.sign_in_with_password(
                {
                    "email": login_request.email,
                    "password": login_request.password,
                }
            )

            if response.user:
                # Create backend JWT token
                token_data = {
                    "sub": response.user.id,
                    "email": response.user.email,
                    "user_id": response.user.id,
                }
                access_token = create_access_token(token_data)

                logger.info(f"User logged in: {response.user.email}")

                return TokenResponse(
                    access_token=access_token,
                    token_type="bearer",
                    expires_in=settings.access_token_expire_minutes * 60,
                )
            return None
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return None

    async def register(
        self, register_request: RegisterRequest
    ) -> Optional[TokenResponse]:
        """Handle user registration using Supabase."""
        try:
            # Register with Supabase
            response = supabase_auth.client.auth.sign_up(
                {
                    "email": register_request.email,
                    "password": register_request.password,
                    "options": {},
                }
            )

            if response.user:
                # Create backend JWT token
                token_data = {
                    "sub": response.user.id,
                    "email": response.user.email,
                    "user_id": response.user.id,
                }
                access_token = create_access_token(token_data)

                logger.info(f"User registered: {response.user.email}")

                return TokenResponse(
                    access_token=access_token,
                    token_type="bearer",
                    expires_in=settings.access_token_expire_minutes * 60,
                )
            return None
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return None

    async def logout(self, current_user: Dict[str, Any]) -> bool:
        """Handle user logout."""
        try:
            # Sign out from Supabase
            supabase_auth.client.auth.sign_out()
            logger.info(f"User logged out: {current_user.get('email')}")
            return True
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            return False

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
        # Get profile from Supabase
        try:
            user = await supabase_auth.verify_token_by_id(user_id)
            if user:
                return UserProfile(
                    user_id=user.id,
                    email=user.email,
                    created_at=user.created_at,
                )
        except Exception:
            pass

        # Fallback to service method
        profile = await self.auth_service.get_user_profile(user_id)
        if not profile:
            raise user_not_found_error()
        return profile

    async def list_api_keys(self, current_user: Dict[str, Any]) -> List[dict]:
        """Handle listing user's API keys."""
        user_id = current_user["sub"]
        return await self.auth_service.list_api_keys(user_id)

    async def delete_api_key(self, current_user: Dict[str, Any], key_id: str) -> bool:
        """Handle API key deletion."""
        user_id = current_user["sub"]
        return await self.auth_service.delete_api_key(user_id, key_id)
