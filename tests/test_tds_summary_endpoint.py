from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.database import Base
from app.gst_service import create_invoice_with_tds
from app.models import User


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


def test_tds_summary_two_professional_invoices_above_30k():
    session = build_session()

    user = User(email="tds_summary_user@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    invoice_1 = create_invoice_with_tds(
        session=session,
        user_id=user.id,
        invoice_number="TDS-001",
        invoice_date="2025-06-10",
        amount=40000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
        vendor_type="professional",
    )
    invoice_2 = create_invoice_with_tds(
        session=session,
        user_id=user.id,
        invoice_number="TDS-002",
        invoice_date="2025-06-20",
        amount=50000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
        vendor_type="professional",
    )

    assert invoice_1.tds_rate == 10.0
    assert invoice_1.tds_amount == 4000.0
    assert invoice_2.tds_rate == 10.0
    assert invoice_2.tds_amount == 5000.0

    tds_summary_route = get_route("/tds-summary/{user_id}/{year_month}")
    summary = tds_summary_route.endpoint(user_id=user.id, year_month="2025-06", db=session)

    assert summary["total_tds_deducted"] == 9000.0
