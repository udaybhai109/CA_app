import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.aging_analysis import calculate_ap_aging, calculate_ar_aging
from app.database import Base
from app.models import Invoice, InvoiceTransactionType, User


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


def seed_aging_invoices(session):
    today = datetime.date.today()
    user = User(email="aging_user@example.com")
    session.add(user)
    session.flush()

    invoices = [
        Invoice(
            user_id=user.id,
            invoice_number="AR-001",
            invoice_date=today - datetime.timedelta(days=10),
            total_amount=100.0,
            gst_rate=18.0,
            is_interstate=False,
            transaction_type=InvoiceTransactionType.SALE,
            cgst=9.0,
            sgst=9.0,
            igst=0.0,
        ),
        Invoice(
            user_id=user.id,
            invoice_number="AR-002",
            invoice_date=today - datetime.timedelta(days=45),
            total_amount=200.0,
            gst_rate=18.0,
            is_interstate=False,
            transaction_type=InvoiceTransactionType.SALE,
            cgst=18.0,
            sgst=18.0,
            igst=0.0,
        ),
        Invoice(
            user_id=user.id,
            invoice_number="AR-003",
            invoice_date=today - datetime.timedelta(days=75),
            total_amount=300.0,
            gst_rate=18.0,
            is_interstate=False,
            transaction_type=InvoiceTransactionType.SALE,
            cgst=27.0,
            sgst=27.0,
            igst=0.0,
        ),
        Invoice(
            user_id=user.id,
            invoice_number="AR-004",
            invoice_date=today - datetime.timedelta(days=120),
            total_amount=400.0,
            gst_rate=18.0,
            is_interstate=False,
            transaction_type=InvoiceTransactionType.SALE,
            cgst=36.0,
            sgst=36.0,
            igst=0.0,
        ),
        Invoice(
            user_id=user.id,
            invoice_number="AP-001",
            invoice_date=today - datetime.timedelta(days=20),
            total_amount=50.0,
            gst_rate=18.0,
            is_interstate=False,
            transaction_type=InvoiceTransactionType.PURCHASE,
            cgst=4.5,
            sgst=4.5,
            igst=0.0,
        ),
        Invoice(
            user_id=user.id,
            invoice_number="AP-002",
            invoice_date=today - datetime.timedelta(days=50),
            total_amount=60.0,
            gst_rate=18.0,
            is_interstate=False,
            transaction_type=InvoiceTransactionType.PURCHASE,
            cgst=5.4,
            sgst=5.4,
            igst=0.0,
        ),
        Invoice(
            user_id=user.id,
            invoice_number="AP-003",
            invoice_date=today - datetime.timedelta(days=85),
            total_amount=70.0,
            gst_rate=18.0,
            is_interstate=False,
            transaction_type=InvoiceTransactionType.PURCHASE,
            cgst=6.3,
            sgst=6.3,
            igst=0.0,
        ),
        Invoice(
            user_id=user.id,
            invoice_number="AP-004",
            invoice_date=today - datetime.timedelta(days=140),
            total_amount=80.0,
            gst_rate=18.0,
            is_interstate=False,
            transaction_type=InvoiceTransactionType.PURCHASE,
            cgst=7.2,
            sgst=7.2,
            igst=0.0,
        ),
    ]

    session.add_all(invoices)
    session.commit()
    session.refresh(user)
    return user


def test_calculate_ar_and_ap_aging():
    session = build_session()
    user = seed_aging_invoices(session)

    ar = calculate_ar_aging(session, user.id)
    ap = calculate_ap_aging(session, user.id)

    assert ar == {"0_30": 100.0, "31_60": 200.0, "61_90": 300.0, "90_plus": 400.0}
    assert ap == {"0_30": 50.0, "31_60": 60.0, "61_90": 70.0, "90_plus": 80.0}


def test_aging_endpoint():
    session = build_session()
    user = seed_aging_invoices(session)

    route = get_route("/aging/{user_id}")
    response = route.endpoint(user_id=user.id, db=session)

    assert response["accounts_receivable"] == {
        "0_30": 100.0,
        "31_60": 200.0,
        "61_90": 300.0,
        "90_plus": 400.0,
    }
    assert response["accounts_payable"] == {
        "0_30": 50.0,
        "31_60": 60.0,
        "61_90": 70.0,
        "90_plus": 80.0,
    }
