"""Auth endpoint rate-limit tests with explicit app/module isolation."""

import importlib
import os
from itertools import count
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.dependencies import get_auth_service
from app.schemas.error_schemas import ErrorCodes
from tests.conftest import assert_error_shape


_CLIENT_HOST_COUNTER = count(60)


def _reset_limiter_state(app) -> None:
    """Best-effort reset of SlowAPI storage between tests."""
    limiter = getattr(getattr(app, "state", None), "limiter", None)
    storage = getattr(limiter, "_storage", None)
    if storage is None:
        return

    for method_name in ("reset", "clear"):
        method = getattr(storage, method_name, None)
        if callable(method):
            try:
                method()
            except TypeError:
                pass
            return


@pytest.fixture
def auth_rate_limited_client():
    """Create a fresh app instance where auth route decorators are rate-limited."""
    env_keys = (
        "RATE_LIMIT_ENABLED",
        "REGISTER_RATE_LIMIT",
        "LOGIN_RATE_LIMIT",
        "GLOBAL_RATE_LIMIT",
    )
    previous = {key: os.environ.get(key) for key in env_keys}

    os.environ["RATE_LIMIT_ENABLED"] = "true"
    os.environ["REGISTER_RATE_LIMIT"] = "2/minute"
    os.environ["LOGIN_RATE_LIMIT"] = "10/minute"
    os.environ["GLOBAL_RATE_LIMIT"] = "1000/minute"

    get_settings.cache_clear()

    import app.controllers as controllers_module
    import app.controllers.auth_controller as auth_controller_module
    import app.controllers.report_controller as report_controller_module
    import app.main as main_module

    with patch("app.models.init_db", return_value=None):
        importlib.reload(auth_controller_module)
        importlib.reload(report_controller_module)
        importlib.reload(controllers_module)
        main_module = importlib.reload(main_module)

    app = main_module.app
    mock_auth_service = Mock()
    mock_auth_service.register_user.side_effect = ValueError(
        f"{ErrorCodes.USER_EXISTS}:Already exists"
    )
    mock_auth_service.login_user.side_effect = ValueError(
        f"{ErrorCodes.AUTH_INVALID_CREDENTIALS}:Invalid email or password"
    )
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    _reset_limiter_state(app)

    host_octet = 1 + ((next(_CLIENT_HOST_COUNTER) - 1) % 254)
    client_host = f"198.51.100.{host_octet}"

    with TestClient(
        app,
        raise_server_exceptions=False,
        client=(client_host, 50000),
    ) as client:
        yield client

    app.dependency_overrides.clear()

    for key, old_value in previous.items():
        if old_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old_value

    get_settings.cache_clear()

    with patch("app.models.init_db", return_value=None):
        importlib.reload(auth_controller_module)
        importlib.reload(report_controller_module)
        importlib.reload(controllers_module)
        importlib.reload(main_module)


def test_register_endpoint_rate_limited_after_threshold(auth_rate_limited_client):
    """Auth register should return 429 once request count exceeds 2/minute."""
    payload = {
        "email": "throttle@example.com",
        "password": "password123",
        "full_name": "Throttle User",
    }

    for _ in range(2):
        resp = auth_rate_limited_client.post("/api/v1/auth/register", json=payload)
        assert resp.status_code == 409

    resp = auth_rate_limited_client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 429
    assert_error_shape(resp.json(), 429, ErrorCodes.SYS_RATE_LIMIT)


def test_login_endpoint_rate_limited_after_threshold(auth_rate_limited_client):
    """Auth login should eventually return 429 under sustained requests."""
    payload = {
        "email": "throttle@example.com",
        "password": "wrong-password",
    }

    saw_auth_response = False
    rate_limited_response = None

    for _ in range(20):
        resp = auth_rate_limited_client.post("/api/v1/auth/login", json=payload)
        if resp.status_code == 401:
            saw_auth_response = True
            continue
        if resp.status_code == 429:
            rate_limited_response = resp
            break

    assert saw_auth_response, "Expected at least one non-rate-limited auth response"
    assert rate_limited_response is not None, "Expected login endpoint to become rate limited"
    assert_error_shape(rate_limited_response.json(), 429, ErrorCodes.SYS_RATE_LIMIT)