from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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


def test_current_ratio_returns_none_when_no_liabilities():
    session = build_session()
    user = User(email="ratio_none_user@example.com")
    session.add(user)
    session.flush()

    cash = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    equity = LedgerAccount(name="Owner Capital", account_type=AccountType.EQUITY, user_id=user.id)
    session.add_all([cash, equity])
    session.commit()
    session.refresh(user)
    session.refresh(cash)
    session.refresh(equity)

    create_transaction(
        session=session,
        user_id=user.id,
        description="Capital",
        debit_account_id=cash.id,
        credit_account_id=equity.id,
        amount=10000.0,
    )

    assert calculate_current_ratio(session, user.id) is None


def test_net_profit_margin_returns_none_when_no_revenue():
    session = build_session()
    user = User(email="margin_none_user@example.com")
    session.add(user)
    session.flush()

    cash = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    expense = LedgerAccount(name="Office Expense", account_type=AccountType.EXPENSE, user_id=user.id)
    equity = LedgerAccount(name="Owner Capital", account_type=AccountType.EQUITY, user_id=user.id)
    session.add_all([cash, expense, equity])
    session.commit()
    session.refresh(user)
    session.refresh(cash)
    session.refresh(expense)
    session.refresh(equity)

    create_transaction(
        session=session,
        user_id=user.id,
        description="Capital",
        debit_account_id=cash.id,
        credit_account_id=equity.id,
        amount=10000.0,
    )
    create_transaction(
        session=session,
        user_id=user.id,
        description="Only expense",
        debit_account_id=expense.id,
        credit_account_id=cash.id,
        amount=2000.0,
    )

    assert calculate_net_profit_margin(session, user.id) is None


def test_cash_runway_returns_none_when_no_expense():
    session = build_session()
    user = User(email="runway_none_user@example.com")
    session.add(user)
    session.flush()

    cash = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    equity = LedgerAccount(name="Owner Capital", account_type=AccountType.EQUITY, user_id=user.id)
    session.add_all([cash, equity])
    session.commit()
    session.refresh(user)
    session.refresh(cash)
    session.refresh(equity)

    create_transaction(
        session=session,
        user_id=user.id,
        description="Capital",
        debit_account_id=cash.id,
        credit_account_id=equity.id,
        amount=8000.0,
    )

    assert calculate_cash_runway(session, user.id) is None
