from sqlalchemy.orm import Session
from app.api.v1.shared.db.session import SessionLocal

def get_db_session() -> Session:
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

