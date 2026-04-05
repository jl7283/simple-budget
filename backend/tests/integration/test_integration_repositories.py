"""
Repository integration tests (real PostgreSQL).

Covers user, budget, and expense repositories with:
- CRUD behavior
- DB constraint enforcement
- rollback behavior on failed transactions
"""

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.models.budget import Budget
from app.models.expense import Expense
from app.models.user import User
from app.repositories.budget_repository import BudgetRepository
from app.repositories.expense_repository import ExpenseRepository
from app.repositories.user_repository import UserRepository


def _new_user(email_prefix: str = "repo") -> User:
    suffix = uuid4().hex[:8]
    return User(
        email=f"{email_prefix}_{suffix}@int.com",
        hashed_password="hashed_password",
        full_name="Repo Test User",
    )


class TestUserRepositoryIntegration:
    def test_crud_roundtrip(self, db_session):
        repo = UserRepository(db_session)

        created = repo.create(_new_user("user_crud"))
        fetched = repo.get_by_id(created.id)
        assert fetched is not None
        assert fetched.email == created.email

        fetched.full_name = "Updated Name"
        updated = repo.update(fetched)
        assert updated.full_name == "Updated Name"

        deleted = repo.delete(created.id)
        assert deleted is True
        assert repo.get_by_id(created.id) is None

    def test_unique_email_constraint(self, db_session):
        repo = UserRepository(db_session)
        email = f"user_unique_{uuid4().hex[:8]}@int.com"

        repo.create(
            User(email=email, hashed_password="h1", full_name="First")
        )

        with pytest.raises(IntegrityError):
            repo.create(
                User(email=email, hashed_password="h2", full_name="Second")
            )
        db_session.rollback()

    def test_transaction_rollback_on_failed_flush(self, db_session):
        email = f"user_rollback_{uuid4().hex[:8]}@int.com"

        db_session.add(User(email=email, hashed_password="h1", full_name="First"))
        db_session.flush()

        db_session.add(User(email=email, hashed_password="h2", full_name="Second"))
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

        row = db_session.execute(
            text("SELECT COUNT(*) AS c FROM users WHERE email = :email"),
            {"email": email},
        ).fetchone()
        assert row.c == 0


class TestBudgetRepositoryIntegration:
    def test_crud_and_lookup_by_user_month(self, db_session):
        user_repo = UserRepository(db_session)
        budget_repo = BudgetRepository(db_session)
        user = user_repo.create(_new_user("budget_crud"))

        created = budget_repo.create(
            Budget(user_id=user.id, month="2024-03", amount=2500)
        )

        by_id = budget_repo.get_by_id(created.id)
        by_user_month = budget_repo.get_by_user_and_month(user.id, "2024-03")
        assert by_id is not None
        assert by_user_month is not None
        assert by_user_month.id == created.id

        by_id.amount = 3100
        updated = budget_repo.update(by_id)
        assert float(updated.amount) == 3100.0

        assert budget_repo.delete(created.id) is True
        assert budget_repo.get_by_id(created.id) is None

    def test_unique_user_month_constraint(self, db_session):
        user_repo = UserRepository(db_session)
        budget_repo = BudgetRepository(db_session)
        user = user_repo.create(_new_user("budget_unique"))

        budget_repo.create(Budget(user_id=user.id, month="2024-04", amount=1200))

        with pytest.raises(IntegrityError):
            budget_repo.create(Budget(user_id=user.id, month="2024-04", amount=1500))
        db_session.rollback()

    def test_rollback_when_budget_amount_constraint_fails(self, db_session):
        user_repo = UserRepository(db_session)
        budget_repo = BudgetRepository(db_session)
        user = user_repo.create(_new_user("budget_rollback"))
        user_id = user.id

        with pytest.raises(IntegrityError):
            budget_repo.create(Budget(user_id=user_id, month="2024-05", amount=0))
        db_session.rollback()

        # After rollback, repository operations should work normally again.
        user_after_rollback = user_repo.create(_new_user("budget_after_rollback"))
        created = budget_repo.create(
            Budget(user_id=user_after_rollback.id, month="2024-06", amount=999)
        )
        persisted = budget_repo.get_by_id(created.id)
        assert persisted is not None
        assert float(persisted.amount) == 999.0


class TestExpenseRepositoryIntegration:
    def test_crud_and_month_range_queries(self, db_session):
        user_repo = UserRepository(db_session)
        expense_repo = ExpenseRepository(db_session)
        user = user_repo.create(_new_user("expense_crud"))

        created = expense_repo.create(
            Expense(
                user_id=user.id,
                amount=25.50,
                category="Food",
                date=date(2024, 3, 10),
                note="Lunch",
            )
        )

        by_id = expense_repo.get_by_id(created.id)
        assert by_id is not None
        assert by_id.category == "Food"

        by_range = expense_repo.get_by_user_and_date_range(
            user.id, date(2024, 3, 1), date(2024, 4, 1)
        )
        assert len(by_range) == 1

        by_month = expense_repo.get_by_user_and_month(user.id, "2024-03")
        assert len(by_month) == 1

        by_id.note = "Updated"
        updated = expense_repo.update(by_id)
        assert updated.note == "Updated"

        assert expense_repo.delete(created.id) is True
        assert expense_repo.get_by_id(created.id) is None

    def test_invalid_month_format_raises_value_error(self, db_session):
        user_repo = UserRepository(db_session)
        expense_repo = ExpenseRepository(db_session)
        user = user_repo.create(_new_user("expense_month"))

        with pytest.raises(ValueError):
            expense_repo.get_by_user_and_month(user.id, "March-2024")

    def test_rollback_when_expense_amount_constraint_fails(self, db_session):
        user_repo = UserRepository(db_session)
        expense_repo = ExpenseRepository(db_session)
        user = user_repo.create(_new_user("expense_rollback"))
        user_id = user.id

        with pytest.raises(IntegrityError):
            expense_repo.create(
                Expense(
                    user_id=user_id,
                    amount=0,
                    category="Invalid",
                    date=date(2024, 3, 10),
                    note=None,
                )
            )
        db_session.rollback()

        # After rollback, repository operations should work normally again.
        user_after_rollback = user_repo.create(_new_user("expense_after_rollback"))
        created = expense_repo.create(
            Expense(
                user_id=user_after_rollback.id,
                amount=44.44,
                category="Transport",
                date=date(2024, 3, 9),
                note=None,
            )
        )
        persisted = expense_repo.get_by_id(created.id)
        assert persisted is not None
        assert float(persisted.amount) == 44.44
