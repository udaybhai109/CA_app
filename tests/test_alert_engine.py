import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.accounting_engine import create_transaction
from app.alert_engine import generate_alerts
from app.database import Base
from app.gst_service import create_invoice_with_tds
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


def test_generate_alerts_has_entries_for_tds_and_low_runway():
    session = build_session()

    user = User(email="alert_user@example.com")
    session.add(user)
    session.flush()

    cash_account = LedgerAccount(name="Cash", account_type=AccountType.ASSET, user_id=user.id)
    expense_account = LedgerAccount(
        name="Office Expense", account_type=AccountType.EXPENSE, user_id=user.id
    )
    capital_account = LedgerAccount(
        name="Owner Capital", account_type=AccountType.EQUITY, user_id=user.id
    )
    session.add_all([cash_account, expense_account, capital_account])
    session.commit()
    session.refresh(user)
    session.refresh(cash_account)
    session.refresh(expense_account)
    session.refresh(capital_account)

    create_transaction(
        session=session,
        user_id=user.id,
        description="Initial capital",
        debit_account_id=cash_account.id,
        credit_account_id=capital_account.id,
        amount=10000.0,
    )
    create_transaction(
        session=session,
        user_id=user.id,
        description="Large monthly expense",
        debit_account_id=expense_account.id,
        credit_account_id=cash_account.id,
        amount=5000.0,
    )

    today = datetime.date.today()
    create_invoice_with_tds(
        session=session,
        user_id=user.id,
        invoice_number="TDS-ALERT-1",
        invoice_date=today.strftime("%Y-%m-%d"),
        amount=40000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
        vendor_type="professional",
    )

    alerts = generate_alerts(session, user.id)
    assert len(alerts) >= 1
