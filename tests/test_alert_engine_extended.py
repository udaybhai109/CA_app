import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.alert_engine as alert_engine_module
from app.accounting_engine import create_transaction
from app.database import Base
from app.gst_service import create_invoice_with_tds
from app.models import AccountType, Invoice, InvoiceTransactionType, LedgerAccount, User


def build_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def test_generate_alerts_includes_due_tds_runway_and_ar_overdue(monkeypatch):
    session = build_session()

    user = User(email="alert_extended_user@example.com")
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
        amount=6000.0,
    )
    create_transaction(
        session=session,
        user_id=user.id,
        description="Expense",
        debit_account_id=expense.id,
        credit_account_id=cash.id,
        amount=3000.0,
    )

    create_invoice_with_tds(
        session=session,
        user_id=user.id,
        invoice_number="TDS-ALERT-X",
        invoice_date="2025-06-12",
        amount=40000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
        vendor_type="professional",
    )

    old_sale_invoice = Invoice(
        user_id=user.id,
        invoice_number="AR-OLD-1",
        invoice_date=datetime.date(2024, 1, 1),
        total_amount=10000.0,
        gst_rate=18.0,
        is_interstate=False,
        transaction_type=InvoiceTransactionType.SALE,
        cgst=900.0,
        sgst=900.0,
        igst=0.0,
    )
    session.add(old_sale_invoice)
    session.commit()

    class FixedDate(datetime.date):
        @classmethod
        def today(cls):
            return cls(2025, 6, 18)

    monkeypatch.setattr(alert_engine_module.datetime, "date", FixedDate)

    alerts = alert_engine_module.generate_alerts(session, user.id)

    assert "GST return due soon." in alerts
    assert any("TDS liability pending:" in alert for alert in alerts)
    assert "Cash runway below 3 months." in alerts
    assert "Receivables overdue more than 90 days." in alerts
