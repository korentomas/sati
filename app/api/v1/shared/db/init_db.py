from app.api.v1.shared.db.base import Base
from app.api.v1.shared.db.session import engine

def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)

def drop_db():
    """Drop all tables."""
    Base.metadata.drop_all(bind=engine)

