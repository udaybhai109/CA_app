from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.database import Base
from app.gst_service import create_invoice_with_gst
from app.models import User
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


def test_audit_logs_after_invoice_and_period_close():
    session = build_session()

    user = User(email="audit_user@example.com", role="ca")
    session.add(user)
    session.commit()
    session.refresh(user)

    create_invoice_with_gst(
        session=session,
        user_id=user.id,
        invoice_number="AUD-001",
        invoice_date="2025-06-10",
        amount=10000.0,
        gst_rate=18.0,
        transaction_type="sale",
        is_interstate=False,
    )
    close_period(session, user.id, "2025-06")

    audit_route = get_route("/audit/{user_id}")
    response = audit_route.endpoint(user_id=user.id, db=session)

    assert "logs" in response
    assert len(response["logs"]) >= 2
