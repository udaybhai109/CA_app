import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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


def test_period_lock_blocks_invoice_creation():
    session = build_session()

    user = User(email="period_lock_user@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)

    close_period(session, user.id, "2025-06")

    with pytest.raises(Exception, match="Period is closed. Cannot modify."):
        create_invoice_with_gst(
            session=session,
            user_id=user.id,
            invoice_number="LOCK-001",
            invoice_date="2025-06-15",
            amount=10000.0,
            gst_rate=18.0,
            transaction_type="sale",
            is_interstate=False,
        )
