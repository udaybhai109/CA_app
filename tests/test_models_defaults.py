from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Invoice, InvoiceTransactionType, RefreshToken, User


def build_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def test_user_role_defaults_to_business():
    session = build_session()
    user = User(email="default_role@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    assert user.role == "business"
    assert user.created_at is not None


def test_invoice_defaults_and_user_relationship():
    session = build_session()
    user = User(email="invoice_rel@example.com")
    session.add(user)
    session.flush()

    invoice = Invoice(
        user_id=user.id,
        invoice_number="INV-REL-1",
        invoice_date=date(2025, 6, 1),
        total_amount=1000.0,
        gst_rate=18.0,
        is_interstate=False,
        transaction_type=InvoiceTransactionType.SALE,
        cgst=90.0,
        sgst=90.0,
        igst=0.0,
    )
    session.add(invoice)
    session.commit()
    session.refresh(user)
    session.refresh(invoice)

    assert invoice.tds_amount == 0.0
    assert invoice.user.id == user.id
    assert user.invoices[0].invoice_number == "INV-REL-1"


def test_refresh_token_user_relationship():
    session = build_session()
    user = User(email="token_rel@example.com")
    session.add(user)
    session.flush()

    refresh_token = RefreshToken(
        user_id=user.id,
        token="hashed_token_value",
        expires_at=datetime(2026, 1, 1),
    )
    session.add(refresh_token)
    session.commit()
    session.refresh(user)

    assert len(user.refresh_tokens) == 1
    assert user.refresh_tokens[0].token == "hashed_token_value"
