"""Database configuration and session management.

This module provides SQLAlchemy engine, session factory, and FastAPI dependency
for database sessions following the dependency injection pattern.
"""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.adapters.outbound.persistence.models import Base
from src.application.config import settings

# Database URL
DATABASE_URL = settings.resolved_database_url

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables() -> None:
    """Create all tables in the database.

    This should be called on application startup or use Alembic migrations.
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session]:
    """FastAPI dependency for database sessions.

    Provides a database session that is automatically closed after the request.

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Commit transaction on success
    except Exception:
        db.rollback()  # Rollback on error
        raise
    finally:
        db.close()


# Type alias for dependency injection
DBSession = Annotated[Session, Depends(get_db)]
