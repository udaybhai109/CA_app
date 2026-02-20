from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.accounting_engine import create_transaction
from app.auth import ALGORITHM, SECRET_KEY, create_access_token
from app.database import Base
from app.forecasting import (
    forecast_cash_balance,
    forecast_expenses,
    forecast_gst_liability,
    forecast_revenue,
)
from app.gst_service import create_invoice_with_gst
from app.models import AccountType, LedgerAccount, User


def build_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def seed_forecast_data(session):
    user = User(email="forecast_user@example.com", role="business")
    session.add(user)
    session.flush()

    cash = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    revenue = LedgerAccount(name="Sales Revenue", account_type=AccountType.REVENUE, user_id=user.id)
    expense = LedgerAccount(name="Office Expense", account_type=AccountType.EXPENSE, user_id=user.id)
    equity = LedgerAccount(name="Owner Capital", account_type=AccountType.EQUITY, user_id=user.id)
    session.add_all([cash, revenue, expense, equity])
    session.commit()
    session.refresh(user)
    session.refresh(cash)
    session.refresh(revenue)
    session.refresh(expense)
    session.refresh(equity)

    create_transaction(
        session=session,
        user_id=user.id,
        description="Capital investment",
        debit_account_id=cash.id,
        credit_account_id=equity.id,
        amount=100000.0,
    )
    create_transaction(
        session=session,
        user_id=user.id,
        description="Revenue booked",
        debit_account_id=cash.id,
        credit_account_id=revenue.id,
        amount=50000.0,
    )
    create_transaction(
        session=session,
        user_id=user.id,
        description="Expense paid",
        debit_account_id=expense.id,
        credit_account_id=cash.id,
        amount=20000.0,
    )

    create_invoice_with_gst(
        session=session,
        user_id=user.id,
        invoice_number="S-001",
        invoice_date=date(2025, 1, 15),
        amount=10000.0,
        gst_rate=18.0,
        transaction_type="sale",
        is_interstate=False,
    )
    create_invoice_with_gst(
        session=session,
        user_id=user.id,
        invoice_number="S-002",
        invoice_date=date(2025, 2, 15),
        amount=20000.0,
        gst_rate=18.0,
        transaction_type="sale",
        is_interstate=False,
    )
    create_invoice_with_gst(
        session=session,
        user_id=user.id,
        invoice_number="P-001",
        invoice_date=date(2025, 2, 20),
        amount=5000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
    )
    return user


def test_forecast_revenue_uses_average_monthly_sales():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    user = seed_forecast_data(session)

    projection = forecast_revenue(session, user.id, months=3)

    assert len(projection) == 3
    assert all(item["projected_revenue"] == 15000.0 for item in projection)


def test_forecast_expenses_uses_historical_invoice_month_count():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    user = seed_forecast_data(session)

    projection = forecast_expenses(session, user.id, months=3)

    assert len(projection) == 3
    assert all(item["projected_expense"] == 10000.0 for item in projection)


def test_forecast_cash_balance_rolls_forward_correctly():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    user = seed_forecast_data(session)

    projection = forecast_cash_balance(session, user.id, months=3)
    balances = [item["projected_cash_balance"] for item in projection]

    assert balances == [135000.0, 140000.0, 145000.0]


def test_forecast_gst_liability_uses_average_net_gst():
    SessionLocal = build_session_factory()
    session = SessionLocal()
    user = seed_forecast_data(session)

    projection = forecast_gst_liability(session, user.id, months=3)

    assert len(projection) == 3
    assert all(item["projected_gst_liability"] == 2250.0 for item in projection)


@pytest.fixture()
def client_and_db(monkeypatch):
    SessionLocal = build_session_factory()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main_module.Base.metadata, "create_all", lambda *args, **kwargs: None)
    main_module.app.dependency_overrides[main_module.get_db] = override_get_db

    with TestClient(main_module.app) as client:
        yield client, SessionLocal

    main_module.app.dependency_overrides.clear()


def _auth_header(user_id: int, role: str) -> dict[str, str]:
    token = create_access_token({"sub": str(user_id), "role": role})
    return {"Authorization": f"Bearer {token}"}


def test_forecast_endpoint_forbids_cross_user_access_for_business(client_and_db):
    client, SessionLocal = client_and_db

    with SessionLocal() as db:
        user_1 = User(email="f_user_1@example.com", role="business")
        user_2 = User(email="f_user_2@example.com", role="business")
        db.add_all([user_1, user_2])
        db.commit()
        db.refresh(user_1)
        db.refresh(user_2)

        response = client.get(
            f"/forecast/{user_2.id}",
            headers=_auth_header(user_1.id, role="business"),
        )
        assert response.status_code == 403


def test_forecast_endpoint_allows_admin_for_other_user(client_and_db):
    client, SessionLocal = client_and_db

    with SessionLocal() as db:
        admin_user = User(email="admin_forecast@example.com", role="admin")
        business_user = User(email="biz_forecast@example.com", role="business")
        db.add_all([admin_user, business_user])
        db.commit()
        db.refresh(admin_user)
        db.refresh(business_user)

        response = client.get(
            f"/forecast/{business_user.id}",
            headers=_auth_header(admin_user.id, role="admin"),
        )
        assert response.status_code == 200
        payload = response.json()
        assert "revenue_projection" in payload
        assert "expense_projection" in payload
        assert "cash_projection" in payload
        assert "gst_projection" in payload
