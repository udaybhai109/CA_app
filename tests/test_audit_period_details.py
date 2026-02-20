from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.database import Base
from app.gst_service import create_invoice_with_gst
from app.models import AccountingPeriod, AuditLog, User
from app.period_service import close_period


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


def test_close_period_is_idempotent_and_creates_single_period_record():
    session = build_session()
    user = User(email="period_idempotent@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    first = close_period(session, user.id, "2025-06")
    second = close_period(session, user.id, "2025-06")

    assert first["message"] == "Period closed successfully."
    assert second["message"] == "Period already closed."
    assert session.query(AccountingPeriod).count() == 1


def test_audit_log_metadata_persisted_for_invoice_creation():
    session = build_session()
    user = User(email="audit_metadata@example.com", role="ca")
    session.add(user)
    session.commit()
    session.refresh(user)

    invoice = create_invoice_with_gst(
        session=session,
        user_id=user.id,
        invoice_number="AUDMETA-1",
        invoice_date="2025-06-01",
        amount=12345.0,
        gst_rate=18.0,
        transaction_type="sale",
        is_interstate=False,
    )

    log = (
        session.query(AuditLog)
        .filter(AuditLog.entity_type == "Invoice", AuditLog.entity_id == invoice.id)
        .first()
    )
    assert log is not None
    assert log.metadata_text is not None
    assert "AUDMETA-1" in log.metadata_text


def test_audit_endpoint_returns_logs_in_descending_timestamp_order():
    session = build_session()
    user = User(email="audit_order@example.com", role="ca")
    session.add(user)
    session.commit()
    session.refresh(user)

    create_invoice_with_gst(
        session=session,
        user_id=user.id,
        invoice_number="AUD-ORDER-1",
        invoice_date="2025-06-01",
        amount=10000.0,
        gst_rate=18.0,
        transaction_type="sale",
        is_interstate=False,
    )
    close_period(session, user.id, "2025-06")

    route = get_route("/audit/{user_id}")
    result = route.endpoint(user_id=user.id, db=session, current_user=user)

    timestamps = [item["timestamp"] for item in result["logs"]]
    assert timestamps == sorted(timestamps, reverse=True)
