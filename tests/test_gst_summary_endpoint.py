from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.database import Base
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


def test_gst_summary_two_sales_one_purchase():
    session = build_session()

    user = User(email="gst_summary_user@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    invoice_route = get_route("/invoice")
    summary_route = get_route("/gst-summary/{user_id}/{year_month}")

    invoice_route.endpoint(
        payload=main_module.InvoiceCreateRequest(
            user_id=user.id,
            invoice_number="INV-001",
            invoice_date="2025-06-05",
            amount=100000.0,
            gst_rate=18.0,
            transaction_type="sale",
            is_interstate=False,
        ),
        db=session,
    )
    invoice_route.endpoint(
        payload=main_module.InvoiceCreateRequest(
            user_id=user.id,
            invoice_number="INV-002",
            invoice_date="2025-06-15",
            amount=50000.0,
            gst_rate=18.0,
            transaction_type="sale",
            is_interstate=False,
        ),
        db=session,
    )
    invoice_route.endpoint(
        payload=main_module.InvoiceCreateRequest(
            user_id=user.id,
            invoice_number="INV-003",
            invoice_date="2025-06-20",
            amount=50000.0,
            gst_rate=18.0,
            transaction_type="purchase",
            is_interstate=False,
        ),
        db=session,
    )

    summary = summary_route.endpoint(user_id=user.id, year_month="2025-06", db=session)

    assert summary["output_gst"] == 27000.0
    assert summary["input_gst"] == 9000.0
    assert summary["net_payable"] == 18000.0
