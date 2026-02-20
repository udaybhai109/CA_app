from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.accounting_engine import create_transaction
from app.database import Base
from app.financial_analysis import (
    calculate_cash_runway,
    calculate_current_ratio,
    calculate_net_profit_margin,
)
from app.models import AccountType, LedgerAccount, User


def build_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def get_route(path: str):
    for route in main_module.app.routes:
        if getattr(route, "path", None) == path:
            return route
    raise AssertionError(f"Route not found: {path}")


def seed_seeddata_style_entries(session):
    user = User(email="seed_style_user@example.com")
    session.add(user)
    session.flush()

    cash_account = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    sales_revenue_account = LedgerAccount(
        name="Sales Revenue", account_type=AccountType.REVENUE, user_id=user.id
    )
    office_expense_account = LedgerAccount(
        name="Office Expense", account_type=AccountType.EXPENSE, user_id=user.id
    )
    owner_capital_account = LedgerAccount(
        name="Owner Capital", account_type=AccountType.EQUITY, user_id=user.id
    )
    accounts_payable_account = LedgerAccount(
        name="Accounts Payable", account_type=AccountType.LIABILITY, user_id=user.id
    )

    session.add_all(
        [
            cash_account,
            sales_revenue_account,
            office_expense_account,
            owner_capital_account,
            accounts_payable_account,
        ]
    )
    session.commit()
    session.refresh(user)
    session.refresh(cash_account)
    session.refresh(sales_revenue_account)
    session.refresh(office_expense_account)
    session.refresh(owner_capital_account)
    session.refresh(accounts_payable_account)

    create_transaction(
        session=session,
        user_id=user.id,
        description="Owner invests into business",
        debit_account_id=cash_account.id,
        credit_account_id=owner_capital_account.id,
        amount=100000.0,
    )
    create_transaction(
        session=session,
        user_id=user.id,
        description="Business earns revenue",
        debit_account_id=cash_account.id,
        credit_account_id=sales_revenue_account.id,
        amount=50000.0,
    )
    create_transaction(
        session=session,
        user_id=user.id,
        description="Business pays office expense",
        debit_account_id=office_expense_account.id,
        credit_account_id=cash_account.id,
        amount=20000.0,
    )

    return user


def test_financial_analysis_with_seed_style_data():
    session = build_session()
    user = seed_seeddata_style_entries(session)

    current_ratio = calculate_current_ratio(session, user.id)
    net_profit_margin = calculate_net_profit_margin(session, user.id)
    cash_runway = calculate_cash_runway(session, user.id)

    assert current_ratio is None
    assert net_profit_margin == 0.6
    assert cash_runway == 6.5


def test_financial_health_endpoint_with_seed_style_data():
    session = build_session()
    user = seed_seeddata_style_entries(session)

    route = get_route("/financial-health/{user_id}")
    response = route.endpoint(user_id=user.id, db=session)

    assert response["current_ratio"] is None
    assert response["net_profit_margin"] == 0.6
    assert response["cash_runway"] == 6.5
