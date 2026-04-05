"""
Integration test fixtures - real PostgreSQL, no mocking.

Prerequisites:
    docker-compose -f docker-compose.test.yml up -d
    pip install python-dotenv

Run from the backend directory:
    pytest tests/integration/ -v
"""

import pytest
import os
from pathlib import Path
from typing import Generator
from unittest.mock import patch


def _find_backend_root():
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pytest.ini").exists():
            return parent
    raise RuntimeError("Cannot find backend root (pytest.ini) from " + str(current))


BACKEND_ROOT = _find_backend_root()
ENV_TEST_PATH = BACKEND_ROOT / ".env.test"

if not ENV_TEST_PATH.exists():
    raise FileNotFoundError(
        "\n\n[Integration tests] Cannot find .env.test at:\n"
        "  " + str(ENV_TEST_PATH) + "\n\n"
        "Backend root detected as: " + str(BACKEND_ROOT) + "\n"
    )


# Load .env.test BEFORE any app import.
# Keep override=False so CI-provided env vars (like DATABASE_URL on port 5432)
# are preserved, while local runs still get defaults from .env.test.
# .env.test sets RATE_LIMIT_ENABLED=false which tells main.py to skip
# SlowAPIMiddleware entirely. This is the correct fix — no middleware
# patching needed.
from dotenv import load_dotenv, dotenv_values
load_dotenv(dotenv_path=str(ENV_TEST_PATH), override=False)

# tests/conftest.py seeds a fake DATABASE_URL for unit test safety.
# For integration tests, swap in .env.test only when DB URL is missing/fake.
current_db_url = os.getenv("DATABASE_URL", "")
if not current_db_url or current_db_url.endswith("/fake"):
    env_values = dotenv_values(str(ENV_TEST_PATH))
    fallback_db_url = env_values.get("DATABASE_URL")
    if fallback_db_url:
        os.environ["DATABASE_URL"] = fallback_db_url


# Clear lru_cache so Settings re-reads the env vars we just loaded.
from app.config import get_settings
get_settings.cache_clear()


# Import app after env is loaded so all settings are correct.
from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

with patch("app.models.init_db", return_value=None):
    from app.main import app

from app.models.base import Base, get_db


_settings = get_settings()
print("\n[Integration] DATABASE_URL = " + _settings.DATABASE_URL)
print("[Integration] RATE_LIMIT_ENABLED = " + str(_settings.RATE_LIMIT_ENABLED))

_engine = create_engine(
    _settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=5,
)


@pytest.fixture(scope="session", autouse=True)
def create_tables():
    """Drop and recreate all tables once per test session."""
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture(scope="function")
def db_session():
    """Session isolated per test using an outer transaction + SAVEPOINT."""
    connection = _engine.connect()
    outer_transaction = connection.begin()
    SessionFactory = sessionmaker(bind=connection, autocommit=False, autoflush=False)
    session = SessionFactory()

    # Open a SAVEPOINT so tests can call commit()/rollback() safely.
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, txn):
        if txn.nested and not txn._parent.nested:
            if connection.in_transaction():
                sess.begin_nested()

    try:
        yield session
    finally:
        event.remove(session, "after_transaction_end", _restart_savepoint)
        session.close()
        if outer_transaction.is_active:
            outer_transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def integration_client(db_session):
    """TestClient wired to the real DB. Rate limiting disabled via .env.test."""
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client

    app.dependency_overrides.clear()


def register_and_login(client, email, password):
    """Register a user and return their JWT access token."""
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert reg.status_code == 201, "Register failed: " + str(reg.json())
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, "Login failed: " + str(login.json())
    return login.json()["access_token"]


def auth_headers(token):
    return {"Authorization": "Bearer " + token}