"""
Sprint 3 dedicated end-to-end flow test.

Flow:
register -> login -> create budget -> add expense -> summary

Each step asserts both API output and resulting DB state.
"""

from sqlalchemy import text

from tests.integration.conftest import auth_headers


def test_e2e_budget_flow(integration_client, db_session):
    email = "e2e_budget_flow@int.com"
    password = "password123"

    register_resp = integration_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "E2E Budget Flow",
        },
    )
    assert register_resp.status_code == 201
    user_id = register_resp.json()["id"]

    login_resp = integration_client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    headers = auth_headers(token)

    budget_resp = integration_client.post(
        "/api/v1/budgets",
        json={"month": "2024-03", "amount": "3000.00"},
        headers=headers,
    )
    assert budget_resp.status_code == 201
    budget_id = budget_resp.json()["budgetId"]

    expense_resp = integration_client.post(
        "/api/v1/expenses",
        json={
            "amount": "120.50",
            "category": "Groceries",
            "date": "2024-03-14",
            "note": "Weekly groceries",
        },
        headers=headers,
    )
    assert expense_resp.status_code == 201
    expense_id = expense_resp.json()["expenseId"]

    summary_resp = integration_client.get(
        "/api/v1/reports/summary?month=2024-03",
        headers=headers,
    )
    assert summary_resp.status_code == 200
    summary_body = summary_resp.json()
    assert summary_body["month"] == "2024-03"
    assert float(summary_body["totalExpenses"]) == 120.50
    assert float(summary_body["totalIncome"]) == 0.0
    assert float(summary_body["net"]) == -120.50

    user_row = db_session.execute(
        text("SELECT id, email FROM users WHERE id = :id"),
        {"id": user_id},
    ).fetchone()
    assert user_row is not None
    assert user_row.email == email

    budget_row = db_session.execute(
        text("SELECT id, user_id, month, amount FROM budgets WHERE id = :id"),
        {"id": budget_id},
    ).fetchone()
    assert budget_row is not None
    assert str(budget_row.user_id) == str(user_id)
    assert budget_row.month == "2024-03"
    assert float(budget_row.amount) == 3000.0

    expense_row = db_session.execute(
        text("SELECT id, user_id, amount, category FROM expenses WHERE id = :id"),
        {"id": expense_id},
    ).fetchone()
    assert expense_row is not None
    assert str(expense_row.user_id) == str(user_id)
    assert float(expense_row.amount) == 120.5
    assert expense_row.category == "Groceries"
