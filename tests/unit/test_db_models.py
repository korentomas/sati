"""Unit tests for database models."""
import pytest
from sqlalchemy.orm import Session
from app.api.v1.shared.db.models import User


class TestUserModel:
    """Test cases for User model."""

    def test_create_user(self, db_session: Session):
        """Test creating a user in database."""
        user = User(
            email="test@example.com",
            password_hash="hashed_password_123"
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.password_hash == "hashed_password_123"
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_user_email_unique(self, db_session: Session):
        """Test that email must be unique."""
        user1 = User(email="test@example.com", password_hash="hash1")
        db_session.add(user1)
        db_session.commit()
        
        user2 = User(email="test@example.com", password_hash="hash2")
        db_session.add(user2)
        
        with pytest.raises(Exception):  # IntegrityError or similar
            db_session.commit()

    def test_user_default_is_active(self, db_session: Session):
        """Test that user is active by default."""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.is_active is True

    def test_user_timestamps(self, db_session: Session):
        """Test that created_at and updated_at are set."""
        user = User(email="test@example.com", password_hash="hash")
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        
        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.created_at == user.updated_at

