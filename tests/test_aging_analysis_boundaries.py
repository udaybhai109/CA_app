import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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


def add_invoice(session, user_id, number, tx_type, days_ago, amount):
    invoice_date = datetime.date.today() - datetime.timedelta(days=days_ago)
    session.add(
        Invoice(
            user_id=user_id,
            invoice_number=number,
            invoice_date=invoice_date,
            total_amount=amount,
            gst_rate=18.0,
            is_interstate=False,
            transaction_type=tx_type,
            cgst=0.0,
            sgst=0.0,
            igst=0.0,
        )
    )


def test_aging_bucket_boundaries_for_ar_and_ap():
    session = build_session()
    user = User(email="aging_boundaries@example.com")
    session.add(user)
    session.flush()

    add_invoice(session, user.id, "AR-30", InvoiceTransactionType.SALE, 30, 100.0)
    add_invoice(session, user.id, "AR-31", InvoiceTransactionType.SALE, 31, 200.0)
    add_invoice(session, user.id, "AR-60", InvoiceTransactionType.SALE, 60, 300.0)
    add_invoice(session, user.id, "AR-61", InvoiceTransactionType.SALE, 61, 400.0)
    add_invoice(session, user.id, "AR-90", InvoiceTransactionType.SALE, 90, 500.0)
    add_invoice(session, user.id, "AR-91", InvoiceTransactionType.SALE, 91, 600.0)

    add_invoice(session, user.id, "AP-30", InvoiceTransactionType.PURCHASE, 30, 150.0)
    add_invoice(session, user.id, "AP-61", InvoiceTransactionType.PURCHASE, 61, 250.0)
    add_invoice(session, user.id, "AP-95", InvoiceTransactionType.PURCHASE, 95, 350.0)
    session.commit()

    ar = calculate_ar_aging(session, user.id)
    ap = calculate_ap_aging(session, user.id)

    assert ar == {"0_30": 100.0, "31_60": 500.0, "61_90": 900.0, "90_plus": 600.0}
    assert ap == {"0_30": 150.0, "31_60": 0.0, "61_90": 250.0, "90_plus": 350.0}
