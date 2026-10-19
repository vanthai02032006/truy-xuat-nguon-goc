from collections.abc import Generator

from app.core.database import SessionLocal


def get_db() -> Generator:
    """Dependency for obtaining database sessions per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
