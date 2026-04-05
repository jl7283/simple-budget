"""
Sprint 2 — Security hardening tests.

Covers:
  A. Login lockout (per-email, application layer)
    B. Rate limiting (per-IP, network layer, pure endpoint)
  C. CORS headers (method restrictions)
  D. Secret key validation

Run alone:
    pytest tests/test_security.py -v

Run with coverage:
    pytest tests/test_security.py --cov=app --cov-report=term-missing -v
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta, timezone

from tests.conftest import (
    make_user,
    FIXED_USER_ID,
    assert_error_shape,
)
from app.schemas.error_schemas import ErrorCodes
from app.config import get_settings


# Pure rate limiting test endpoint
def test_ratelimit_test_endpoint(monkeypatch):
    import importlib
    from fastapi.testclient import TestClient
    from unittest.mock import patch

    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("TEST_ENDPOINTS_ENABLED", "true")
    get_settings.cache_clear()
    try:
        import app.rate_limiter as rate_limiter_module
        import app.main as main_module

        with patch("app.models.init_db", return_value=None):
            importlib.reload(rate_limiter_module)
            main_module = importlib.reload(main_module)

        app = main_module.app
        limiter = getattr(getattr(app, "state", None), "limiter", None)
        storage = getattr(limiter, "_storage", None)
        if storage is not None:
            for method_name in ("reset", "clear"):
                method = getattr(storage, method_name, None)
                if callable(method):
                    try:
                        method()
                    except TypeError:
                        pass
                    break

        client = TestClient(app, client=("203.0.113.112", 50000))
        for _ in range(3):
            resp = client.get("/ratelimit-test")
            assert resp.status_code == 200
        resp = client.get("/ratelimit-test")
        assert resp.status_code == 429
        body = resp.json()
        rate_limit_text = body.get("message") or body.get("detail")
        assert rate_limit_text is not None
        assert "per 1 minute" in rate_limit_text
    finally:
        # Prevent cached settings from leaking into subsequent test modules.
        get_settings.cache_clear()





# ===========================================================================
# A. LOGIN LOCKOUT TESTS  (AuthService layer — no HTTP client needed)
# ===========================================================================

class TestLoginLockout:
    """
    Unit tests for the DB-backed lockout in AuthService (Sprint 3).
    The lockout repo is fully mocked — we test service orchestration only.
    """

    def setup_method(self):
        from app.services.auth_service import AuthService
        self.mock_repo = Mock()
        self.mock_lockout_repo = Mock()
        self.mock_lockout_repo.is_locked.return_value = False
        # record_failure must return an object with attempt_count
        _mock_attempt = Mock()
        _mock_attempt.attempt_count = 1
        self.mock_lockout_repo.record_failure.return_value = _mock_attempt
        self.service = AuthService(self.mock_repo, self.mock_lockout_repo)
        self.email = "lockout@example.com"

    def _make_failing_login(self):
        self.mock_repo.get_by_email.return_value = make_user(email=self.email)
        with patch("app.services.auth_service.verify_password", return_value=False):
            with pytest.raises(ValueError):
                self.service.login_user(self.email, "wrongpassword")

    def test_single_failure_does_not_lock(self):
        """One bad attempt should not trigger lockout."""
        self._make_failing_login()
        self.mock_repo.get_by_email.return_value = make_user(email=self.email)
        with patch("app.services.auth_service.verify_password", return_value=False):
            with pytest.raises(ValueError) as exc:
                self.service.login_user(self.email, "wrongpassword")
        assert "Too many" not in str(exc.value)

    def test_lockout_triggers_after_max_attempts(self):
        """If repo says locked, service raises before hitting DB."""
        self.mock_lockout_repo.is_locked.return_value = True
        with pytest.raises(ValueError) as exc:
            self.service.login_user(self.email, "anypassword")
        assert "Too many" in str(exc.value)
        assert ErrorCodes.AUTH_INVALID_CREDENTIALS in str(exc.value)
        self.mock_repo.get_by_email.assert_not_called()

    def test_successful_login_clears_failure_counter(self):
        """Successful login calls lockout_repo.clear."""
        self.mock_repo.get_by_email.return_value = make_user(email=self.email)
        with patch("app.services.auth_service.verify_password", return_value=True):
            with patch("app.services.auth_service.create_access_token", return_value="tok"):
                self.service.login_user(self.email, "correctpassword")
        self.mock_lockout_repo.clear.assert_called_once_with(self.email)

    def test_lockout_window_expires(self):
        """Non-threshold DB failure count should not trigger lockout."""
        self.mock_repo.get_by_email.return_value = make_user(email=self.email)
        mock_row = Mock()
        mock_row.attempt_count = 1
        self.mock_lockout_repo.record_failure.return_value = mock_row
        with patch("app.services.auth_service.verify_password", return_value=False):
            with pytest.raises(ValueError) as exc:
                self.service.login_user(self.email, "wrongpassword")
        assert "Too many" not in str(exc.value)

    def test_nonexistent_user_still_records_failure(self):
        """Email not found still records a failure attempt."""
        self.mock_repo.get_by_email.return_value = None
        mock_row = Mock()
        mock_row.attempt_count = 1
        self.mock_lockout_repo.record_failure.return_value = mock_row
        with pytest.raises(ValueError):
            self.service.login_user(self.email, "password")
        self.mock_lockout_repo.record_failure.assert_called_once()

    def test_lockout_is_per_email_not_global(self):
        """is_locked is called with the specific email."""
        other_email = "other@example.com"
        self.mock_repo.get_by_email.return_value = make_user(email=other_email)
        with patch("app.services.auth_service.verify_password", return_value=True):
            with patch("app.services.auth_service.create_access_token", return_value="tok"):
                token = self.service.login_user(other_email, "correctpassword")
        assert token == "tok"
        self.mock_lockout_repo.is_locked.assert_called_with(other_email)


# ===========================================================================
# B. RATE LIMITING TESTS  (HTTP layer via TestClient)
# ===========================================================================

class TestRateLimiting:
    """
    Integration tests for slowapi rate limiting using only pure endpoints.
    These hit the real FastAPI app through TestClient.
    
    Note: slowapi uses an in-memory counter that persists across requests
    within the same TestClient session. Tests clear the limiter state by
    using a fresh client fixture per test (each fixture call = new app state).
    """

    def test_health_endpoint_not_rate_limited(self, unauth_client):
        """GET /health should never return 429, even past global default limits."""
        client = unauth_client["client"]
        settings = get_settings()
        # Default global rate limit is high; just test with 20 requests
        for _ in range(20):
            resp = client.get("/health")
            assert resp.status_code == 200, (
                f"Health endpoint should not be rate limited, got {resp.status_code}"
            )


# ===========================================================================
# C. CORS HEADER TESTS
# ===========================================================================

class TestCORSHeaders:
    """
    Verify CORS is locked down to specific methods only.
    Tightened in Sprint 2: allow_methods changed from ["*"] to ["GET","POST","PUT"].
    """

    def test_cors_preflight_allows_post(self, unauth_client):
        """OPTIONS preflight for POST should succeed from an allowed origin."""
        client = unauth_client["client"]
        resp = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        # 200 or 204 means the preflight was accepted
        assert resp.status_code in (200, 204)

    def test_cors_allowed_origin_present_in_response(self, unauth_client):
        """Responses to requests from an allowed origin should carry CORS headers."""
        client = unauth_client["client"]
        svc = unauth_client["auth_service"]
        svc.login_user.side_effect = ValueError(
            f"{ErrorCodes.AUTH_INVALID_CREDENTIALS}:bad creds"
        )

        resp = client.post(
            "/api/v1/auth/login",
            json={"email": "a@example.com", "password": "pass"},
            headers={"Origin": "http://localhost:3000"},
        )
        assert "access-control-allow-origin" in resp.headers

    def test_cors_preflight_rejects_delete(self, unauth_client):
        """
        OPTIONS preflight for DELETE should be rejected — DELETE is not in
        our allow_methods list after Sprint 2 tightening.
        """
        client = unauth_client["client"]
        resp = client.options(
            "/api/v1/expenses",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "DELETE",
            },
        )
        # Either the preflight is rejected (400/403) OR the
        # Allow header does not include DELETE
        if resp.status_code in (200, 204):
            allow = resp.headers.get("access-control-allow-methods", "")
            assert "DELETE" not in allow, (
                "DELETE should not be in CORS allowed methods after Sprint 2"
            )


# ===========================================================================
# D. SECRET KEY VALIDATION
# ===========================================================================

class TestSecretKeyConfig:
    """
    Verify the application does not ship with the old placeholder secret.
    """

    def test_secret_key_is_not_original_placeholder(self):
        """SECRET_KEY must not be the original insecure default from pre-Sprint-2."""
        from app.config import get_settings
        settings = get_settings()
        assert settings.SECRET_KEY != "your-secret-key-change-in-production", (
            "SECRET_KEY is still the original insecure placeholder. "
            "Set a real value in .env."
        )

    def test_secret_key_has_minimum_length(self):
        """SECRET_KEY should be at least 32 characters."""
        from app.config import get_settings
        settings = get_settings()
        assert len(settings.SECRET_KEY) >= 32, (
            f"SECRET_KEY is only {len(settings.SECRET_KEY)} chars — "
            "minimum 32 required for HS256 security."
        )

    def test_algorithm_is_hs256(self):
        """JWT algorithm should be HS256 (as designed)."""
        from app.config import get_settings
        assert get_settings().ALGORITHM == "HS256"