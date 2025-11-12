import secrets
import uuid
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from app.api.v1.features.authentication.dto import (
    ApiKeyRequest,
    ApiKeyResponse,
    LoginRequest,
    TokenResponse,
    UserProfile,
)
from app.api.v1.shared.auth.jwt import create_access_token, verify_password, get_password_hash
from app.api.v1.shared.db.models import User
from app.core.config import settings


class AuthService:
    """Authentication service with database."""

    def __init__(self, db: Session):
        self.db = db

    # Mock API keys storage (TODO: move to DB)
    _api_keys: dict = {}

    def register_user(self, email: str, password: str) -> User:
        """Register a new user with password hashing."""
        # Check if user exists
        existing_user = self.db.query(User).filter(User.email == email).first()
        if existing_user:
            raise ValueError("User already exists")
        
        # Hash password
        password_hash = get_password_hash(password)
        
        # Create user
        user = User(email=email, password_hash=password_hash)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        # Find user
        user = self.db.query(User).filter(
            User.email == email,
            User.is_active == True
        ).first()
        
        if not user:
            return None
        
        # Verify password
        if not verify_password(password, user.password_hash):
            return None
        
        return user

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

    def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID."""
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            return None
        user = self.db.query(User).filter(User.id == user_uuid).first()
        if not user:
            return None
        return UserProfile(
            user_id=str(user.id),
            email=user.email,
            created_at=user.created_at.isoformat() if user.created_at else "",
        )

    async def list_api_keys(self, user_id: str) -> List[dict]:
        """List all API keys for a user."""
        user_keys = []
        for key_data in self._api_keys.values():
            if key_data["user_id"] == user_id:
                # Don't return the actual API key, only metadata
                key_info = key_data.copy()
                key_info.pop("api_key", None)
                user_keys.append(key_info)
        return user_keys

    async def delete_api_key(self, user_id: str, key_id: str) -> bool:
        """Delete an API key if it belongs to the user."""
        if key_id in self._api_keys and self._api_keys[key_id]["user_id"] == user_id:
            del self._api_keys[key_id]
            return True
        return False
