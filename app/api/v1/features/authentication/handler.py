from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

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
from app.core.config import settings
from app.core.logging import logger


class AuthHandler:
    """Authentication handler for orchestrating service calls."""

    def __init__(self, db: Optional[Session] = None) -> None:
        self.db = db
        if db:
            self.auth_service: Optional[AuthService] = AuthService(db)
        else:
            self.auth_service = None

    def login(self, login_request: LoginRequest) -> Optional[TokenResponse]:
        """Handle user login with password verification."""
        if not self.auth_service:
            return None
        try:
            # Authenticate user
            user = self.auth_service.authenticate_user(
                login_request.email, login_request.password
            )

            if not user:
                return None

            # Create JWT token
            token_data = {
                "sub": str(user.id),
                "email": user.email,
                "user_id": str(user.id),
            }
            access_token = create_access_token(token_data)

            logger.info(f"User logged in: {user.email}")

            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
            )
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return None

    def register(self, register_request: RegisterRequest) -> Optional[TokenResponse]:
        """Handle user registration with password hashing."""
        if not self.auth_service:
            return None
        try:
            # Create user with hashed password
            user = self.auth_service.register_user(
                register_request.email, register_request.password
            )

            # Create JWT token
            token_data = {
                "sub": str(user.id),
                "email": user.email,
                "user_id": str(user.id),
            }
            access_token = create_access_token(token_data)

            logger.info(f"User registered: {user.email}")

            return TokenResponse(
                access_token=access_token,
                token_type="bearer",
                expires_in=settings.access_token_expire_minutes * 60,
            )
        except ValueError:
            # Propagate ValueError (e.g., "User already exists") to router
            raise
        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return None

    def logout(self, current_user: Dict[str, Any]) -> bool:
        """Handle user logout."""
        logger.info(f"User logged out: {current_user.get('email')}")
        return True

    async def create_api_key(
        self, current_user: Dict[str, Any], request: ApiKeyRequest
    ) -> ApiKeyResponse:
        """Handle API key creation."""
        if not self.auth_service:
            raise api_key_creation_error()
        try:
            user_id = current_user["sub"]
            api_key_response = await self.auth_service.create_api_key(user_id, request)
            return api_key_response
        except Exception:
            raise api_key_creation_error()

    def get_profile(self, current_user: Dict[str, Any]) -> UserProfile:
        """Handle user profile retrieval."""
        if not self.auth_service:
            raise user_not_found_error()
        user_id = current_user["sub"]
        profile = self.auth_service.get_user_profile(user_id)
        if not profile:
            raise user_not_found_error()
        return profile

    async def list_api_keys(self, current_user: Dict[str, Any]) -> List[dict]:
        """Handle listing user's API keys."""
        if not self.auth_service:
            return []
        user_id = current_user["sub"]
        return await self.auth_service.list_api_keys(user_id)

    async def delete_api_key(self, current_user: Dict[str, Any], key_id: str) -> bool:
        """Handle API key deletion."""
        if not self.auth_service:
            return False
        user_id = current_user["sub"]
        return await self.auth_service.delete_api_key(user_id, key_id)
