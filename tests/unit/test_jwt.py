"""Unit tests for JWT and password hashing."""
import pytest
from datetime import timedelta
from app.api.v1.shared.auth.jwt import (
    create_access_token,
    verify_token,
    get_password_hash,
    verify_password
)


class TestJWT:
    """Test cases for JWT token creation and verification."""

    def test_create_access_token(self):
        """Test creating an access token."""
        data = {"sub": "user-123", "email": "test@example.com"}
        token = create_access_token(data)
        
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_token_success(self):
        """Test verifying a valid token."""
        data = {"sub": "user-123", "email": "test@example.com"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload

    def test_verify_token_invalid(self):
        """Test verifying an invalid token."""
        payload = verify_token("invalid_token_string")
        
        assert payload is None

    def test_verify_token_missing_sub(self):
        """Test that token without 'sub' field is rejected."""
        # Create token without 'sub'
        from jose import jwt
        from app.core.config import settings
        
        token = jwt.encode(
            {"email": "test@example.com"},
            settings.secret_key,
            algorithm=settings.algorithm
        )
        
        payload = verify_token(token)
        
        assert payload is None

    def test_token_expiration(self):
        """Test that token expires correctly."""
        data = {"sub": "user-123"}
        # Create token with very short expiration
        token = create_access_token(data, expires_delta=timedelta(seconds=-1))
        
        # Token should be expired
        payload = verify_token(token)
        
        assert payload is None


class TestPasswordHashing:
    """Test cases for password hashing and verification."""

    @pytest.mark.parametrize("password", [
        "simple",
        "complex_password_123!@#",
        "123456",
    ])
    def test_password_hashing(self, password: str):
        """Test that passwords are hashed correctly."""
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different (due to salt)
        assert hash1 != hash2
        
        # But both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_password_verification_success(self):
        """Test successful password verification."""
        password = "secret123"
        password_hash = get_password_hash(password)
        
        assert verify_password(password, password_hash) is True

    def test_password_verification_failure(self):
        """Test password verification with wrong password."""
        password = "secret123"
        password_hash = get_password_hash(password)
        
        assert verify_password("wrong_password", password_hash) is False

    def test_different_passwords_different_hashes(self):
        """Test that different passwords produce different hashes."""
        hash1 = get_password_hash("password1")
        hash2 = get_password_hash("password2")
        
        assert hash1 != hash2

