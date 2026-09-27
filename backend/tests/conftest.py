"""Pytest configuration and fixtures.

This module provides shared test fixtures including the FastAPI test client
with proper database isolation for integration tests.
"""

import os

# Set dummy environment variables for testing BEFORE importing the app
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("GOOGLE_AUTH_URL", "https://accounts.google.com/o/oauth2/v2/auth")
os.environ.setdefault("GOOGLE_TOKEN_URL", "https://oauth2.googleapis.com/token")
os.environ.setdefault("GOOGLE_CERTS_URL", "https://www.googleapis.com/oauth2/v3/certs")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:8001/auth/google/callback")
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")
os.environ.setdefault("APP_ENV", "test")

from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from src.adapters.outbound.persistence.database import get_db
from src.adapters.outbound.persistence.models import Base
from src.main import app

# Use in-memory SQLite for testing to avoid external dependencies
TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db() -> Generator[Session]:
    """Override database dependency for testing."""
    db = TestSessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@pytest.fixture(scope="function", autouse=True)
def setup_database() -> Generator[None]:
    """Create fresh database tables before each test and drop after."""
    # Create all tables
    Base.metadata.create_all(bind=test_engine)
    yield
    # Drop all tables after test to ensure clean state
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client() -> Generator[TestClient]:
    """Provide a test client with database dependency overridden."""
    app.dependency_overrides[get_db] = override_get_db
    with patch("src.main.create_tables"), TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
