import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.accounting_engine import calculate_total_balance, create_transaction
from app.database import Base
from app.models import AccountType, JournalEntry, LedgerAccount, User


def build_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def test_calculate_total_balance_sums_debit_minus_credit():
    entries = [
        JournalEntry(
            transaction_id=1,
            ledger_account_id=1,
            debit_amount=100.0,
            credit_amount=0.0,
        ),
        JournalEntry(
            transaction_id=1,
            ledger_account_id=2,
            debit_amount=0.0,
            credit_amount=30.0,
        ),
        JournalEntry(
            transaction_id=2,
            ledger_account_id=3,
            debit_amount=20.0,
            credit_amount=0.0,
        ),
    ]

    assert calculate_total_balance(entries) == 90.0


def test_create_transaction_rejects_non_positive_amount():
    session = build_session()
    user = User(email="txn_validation@example.com")
    session.add(user)
    session.flush()
    cash = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    equity = LedgerAccount(name="Capital", account_type=AccountType.EQUITY, user_id=user.id)
    session.add_all([cash, equity])
    session.commit()
    session.refresh(user)
    session.refresh(cash)
    session.refresh(equity)

    with pytest.raises(ValueError, match="Amount must be greater than 0."):
        create_transaction(
            session=session,
            user_id=user.id,
            description="invalid amount",
            debit_account_id=cash.id,
            credit_account_id=equity.id,
            amount=0.0,
        )
