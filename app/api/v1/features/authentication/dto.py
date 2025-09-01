from typing import Optional

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """Login request schema."""

    email: str
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str
    expires_in: int


class ApiKeyRequest(BaseModel):
    """API key generation request."""

    name: str
    description: Optional[str] = None


class ApiKeyResponse(BaseModel):
    """API key response schema."""

    key_id: str
    api_key: str
    name: str
    description: Optional[str]
    created_at: str
    expires_at: Optional[str]


class UserProfile(BaseModel):
    """User profile schema."""

    user_id: str
    email: str
    created_at: str
