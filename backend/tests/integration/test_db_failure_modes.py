"""
Integration tests for DB failure modes.

Simulates database disconnects, timeouts, and transaction failures
while calling real API endpoints. Assertions ensure graceful JSON
error responses (no unhandled crashes).
"""

import pytest
from sqlalchemy.exc import OperationalError, SQLAlchemyError, TimeoutError as SATimeoutError

from app.schemas.error_schemas import ErrorCodes
from tests.integration.conftest import auth_headers, register_and_login


_REQUIRED_FIELDS = {"timestamp", "status", "error", "errorCode", "message", "path"}


def _assert_db_failure_envelope(resp, expected_path: str):
    assert resp.status_code == 500
    body = resp.json()
    missing = _REQUIRED_FIELDS - set(body.keys())
    assert not missing, f"Missing error envelope fields: {missing}. Body: {body}"
    assert body["errorCode"] == ErrorCodes.SYS_DATABASE_ERROR
    assert body["status"] == 500
    assert body["path"] == expected_path


class TestDatabaseFailureModes:
    def test_register_gracefully_handles_db_disconnect(
        self, integration_client, db_session, monkeypatch
    ):
        """Simulate DB disconnect during commit on /auth/register."""

        def _raise_disconnect(*_args, **_kwargs):
            raise OperationalError(
                "COMMIT",
                {},
                Exception("connection lost"),
            )

        monkeypatch.setattr(db_session, "commit", _raise_disconnect)

        resp = integration_client.post(
            "/api/v1/auth/register",
            json={
                "email": "disconnect@int.com",
                "password": "password123",
                "full_name": "Disconnect",
            },
        )

        _assert_db_failure_envelope(resp, "/api/v1/auth/register")

    def test_summary_gracefully_handles_db_timeout(
        self, integration_client, db_session, monkeypatch
    ):
        """Simulate query timeout while generating /reports/summary."""
        token = register_and_login(integration_client, "timeout@int.com", "password123")

        def _raise_timeout(*_args, **_kwargs):
            raise SATimeoutError("statement timeout")

        monkeypatch.setattr(db_session, "execute", _raise_timeout)

        resp = integration_client.get(
            "/api/v1/reports/summary?month=2024-03",
            headers=auth_headers(token),
        )

        _assert_db_failure_envelope(resp, "/api/v1/reports/summary")

    def test_budget_create_gracefully_handles_transaction_failure(
        self, integration_client, db_session, monkeypatch
    ):
        """Simulate transaction failure during /budgets commit."""
        token = register_and_login(integration_client, "txfail@int.com", "password123")

        def _raise_tx_failure(*_args, **_kwargs):
            raise SQLAlchemyError("transaction aborted")

        monkeypatch.setattr(db_session, "commit", _raise_tx_failure)

        resp = integration_client.post(
            "/api/v1/budgets",
            json={"month": "2024-08", "amount": "2200.00"},
            headers=auth_headers(token),
        )

        _assert_db_failure_envelope(resp, "/api/v1/budgets")
