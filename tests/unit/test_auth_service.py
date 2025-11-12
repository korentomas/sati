"""Unit tests for AuthService."""
import pytest
from sqlalchemy.orm import Session
from app.api.v1.features.authentication.service import AuthService
from app.api.v1.shared.db.models import User


class TestAuthService:
    """Test cases for AuthService."""

    def test_register_user_success(self, db_session: Session):
        """Test successful user registration."""
        service = AuthService(db_session)
        
        user = service.register_user("newuser@example.com", "password123")
        
        assert user.id is not None
        assert user.email == "newuser@example.com"
        assert user.password_hash != "password123"  # Should be hashed
        assert user.is_active is True
        
        # Verify user is in database
        db_user = db_session.query(User).filter(User.email == "newuser@example.com").first()
        assert db_user is not None
        assert db_user.email == "newuser@example.com"

    def test_register_user_duplicate_email(self, db_session: Session):
        """Test registration with duplicate email fails."""
        service = AuthService(db_session)
        
        # Register first user
        service.register_user("test@example.com", "password123")
        
        # Try to register again with same email
        with pytest.raises(ValueError, match="User already exists"):
            service.register_user("test@example.com", "password456")

    def test_authenticate_user_success(self, db_session: Session):
        """Test successful authentication."""
        service = AuthService(db_session)
        
        # Register user
        user = service.register_user("test@example.com", "password123")
        
        # Authenticate
        authenticated = service.authenticate_user("test@example.com", "password123")
        
        assert authenticated is not None
        assert authenticated.id == user.id
        assert authenticated.email == "test@example.com"

    def test_authenticate_user_wrong_password(self, db_session: Session):
        """Test authentication with wrong password."""
        service = AuthService(db_session)
        
        # Register user
        service.register_user("test@example.com", "password123")
        
        # Try wrong password
        authenticated = service.authenticate_user("test@example.com", "wrongpassword")
        
        assert authenticated is None

    def test_authenticate_user_nonexistent(self, db_session: Session):
        """Test authentication with non-existent user."""
        service = AuthService(db_session)
        
        authenticated = service.authenticate_user("nonexistent@example.com", "password123")
        
        assert authenticated is None

    def test_authenticate_user_inactive(self, db_session: Session):
        """Test that inactive users cannot authenticate."""
        service = AuthService(db_session)
        
        # Register user
        user = service.register_user("test@example.com", "password123")
        
        # Deactivate user
        user.is_active = False
        db_session.commit()
        
        # Try to authenticate
        authenticated = service.authenticate_user("test@example.com", "password123")
        
        assert authenticated is None

    def test_get_user_profile_success(self, db_session: Session):
        """Test getting user profile."""
        service = AuthService(db_session)
        
        # Register user
        user = service.register_user("test@example.com", "password123")
        
        # Get profile
        profile = service.get_user_profile(str(user.id))
        
        assert profile is not None
        assert profile.user_id == str(user.id)
        assert profile.email == "test@example.com"
        assert profile.created_at is not None

    def test_get_user_profile_nonexistent(self, db_session: Session):
        """Test getting profile for non-existent user."""
        service = AuthService(db_session)
        
        profile = service.get_user_profile("00000000-0000-0000-0000-000000000000")
        
        assert profile is None

