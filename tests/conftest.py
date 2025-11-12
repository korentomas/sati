from typing import Callable, Dict, Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.api.v1.shared.db.base import Base
from app.api.v1.shared.db.deps import get_db_session


# Test database (SQLite in memory for fast tests)
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a test database session."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    
    # Create session
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application with test database."""
    # Ensure tables are created in the same engine
    Base.metadata.create_all(bind=test_engine)
    
    # Override get_db_session dependency to use test database
    # Create a new session from the same engine to ensure tables exist
    def override_get_db():
        session = TestSessionLocal()
        try:
            # Ensure tables exist
            Base.metadata.create_all(bind=test_engine)
            yield session
        finally:
            session.rollback()
            session.close()
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    yield TestClient(app)
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def valid_login_data() -> Dict[str, str]:
    """Valid login credentials for testing."""
    return {"email": "email@example.com", "password": "secret"}


@pytest.fixture
def valid_api_key_request() -> Dict[str, str]:
    """Valid API key request for testing."""
    return {"name": "Test API Key", "description": "Test API key for testing purposes"}


@pytest.fixture
def auth_headers() -> Callable[[str], Dict[str, str]]:
    """Get authentication headers for protected endpoints."""

    def _get_auth_headers(access_token: str) -> Dict[str, str]:
        return {"Authorization": f"Bearer {access_token}"}

    return _get_auth_headers
