from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.gst_service import (
    create_invoice_with_gst,
    create_invoice_with_tds,
    generate_monthly_gst_summary,
    generate_monthly_tds_summary,
)
from app.models import AccountingPeriod, Invoice, TDSLiability, TaxLiability, User


def build_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def seed_user(session, email="gst_edge_user@example.com"):
    user = User(email=email)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_create_invoice_with_gst_interstate_sets_igst_only():
    session = build_session()
    user = seed_user(session)

    invoice = create_invoice_with_gst(
        session=session,
        user_id=user.id,
        invoice_number="EDGE-IGST-1",
        invoice_date=date(2025, 6, 10),
        amount=100000.0,
        gst_rate=18.0,
        transaction_type="sale",
        is_interstate=True,
    )

    assert invoice.cgst == 0.0
    assert invoice.sgst == 0.0
    assert invoice.igst == 18000.0


def test_create_invoice_with_gst_invalid_transaction_type_raises():
    session = build_session()
    user = seed_user(session, "invalid_tx_type@example.com")

    with pytest.raises(ValueError, match="transaction_type must be 'sale' or 'purchase'"):
        create_invoice_with_gst(
            session=session,
            user_id=user.id,
            invoice_number="EDGE-INVALID-1",
            invoice_date=date(2025, 6, 10),
            amount=1000.0,
            gst_rate=18.0,
            transaction_type="invalid",
            is_interstate=False,
        )


def test_generate_monthly_gst_summary_updates_existing_row():
    session = build_session()
    user = seed_user(session, "gst_upsert_user@example.com")

    create_invoice_with_gst(
        session=session,
        user_id=user.id,
        invoice_number="UPSERT-1",
        invoice_date=date(2025, 6, 5),
        amount=100000.0,
        gst_rate=18.0,
        transaction_type="sale",
        is_interstate=False,
    )
    first_summary = generate_monthly_gst_summary(session, user.id, "2025-06")
    assert first_summary == {"output_gst": 18000.0, "input_gst": 0.0, "net_payable": 18000.0}
    assert session.query(TaxLiability).count() == 1

    create_invoice_with_gst(
        session=session,
        user_id=user.id,
        invoice_number="UPSERT-2",
        invoice_date=date(2025, 6, 20),
        amount=50000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
    )
    second_summary = generate_monthly_gst_summary(session, user.id, "2025-06")

    assert second_summary == {"output_gst": 18000.0, "input_gst": 9000.0, "net_payable": 9000.0}
    assert session.query(TaxLiability).count() == 1
    liability = session.query(TaxLiability).first()
    assert liability.period_month == "2025-06"
    assert liability.net_gst_payable == 9000.0


def test_generate_monthly_gst_summary_filters_by_requested_month():
    session = build_session()
    user = seed_user(session, "gst_filter_user@example.com")

    create_invoice_with_gst(
        session=session,
        user_id=user.id,
        invoice_number="MAY-1",
        invoice_date=date(2025, 5, 31),
        amount=100000.0,
        gst_rate=18.0,
        transaction_type="sale",
        is_interstate=False,
    )
    create_invoice_with_gst(
        session=session,
        user_id=user.id,
        invoice_number="JUNE-1",
        invoice_date=date(2025, 6, 1),
        amount=100000.0,
        gst_rate=18.0,
        transaction_type="sale",
        is_interstate=False,
    )

    may_summary = generate_monthly_gst_summary(session, user.id, "2025-05")
    june_summary = generate_monthly_gst_summary(session, user.id, "2025-06")

    assert may_summary["output_gst"] == 18000.0
    assert june_summary["output_gst"] == 18000.0
    assert session.query(TaxLiability).count() == 2


def test_create_invoice_with_tds_applies_threshold_rules():
    session = build_session()
    user = seed_user(session, "tds_threshold_user@example.com")

    above_threshold = create_invoice_with_tds(
        session=session,
        user_id=user.id,
        invoice_number="TDS-A",
        invoice_date=date(2025, 6, 11),
        amount=40000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
        vendor_type="professional",
    )
    below_threshold = create_invoice_with_tds(
        session=session,
        user_id=user.id,
        invoice_number="TDS-B",
        invoice_date=date(2025, 6, 12),
        amount=30000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
        vendor_type="professional",
    )
    non_professional = create_invoice_with_tds(
        session=session,
        user_id=user.id,
        invoice_number="TDS-C",
        invoice_date=date(2025, 6, 13),
        amount=50000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
        vendor_type="contractor",
    )

    assert above_threshold.tds_rate == 10.0
    assert above_threshold.tds_amount == 4000.0
    assert below_threshold.tds_rate == 0.0
    assert below_threshold.tds_amount == 0.0
    assert non_professional.tds_rate == 0.0
    assert non_professional.tds_amount == 0.0


def test_generate_monthly_tds_summary_updates_existing_row():
    session = build_session()
    user = seed_user(session, "tds_upsert_user@example.com")

    create_invoice_with_tds(
        session=session,
        user_id=user.id,
        invoice_number="TUP-1",
        invoice_date=date(2025, 6, 2),
        amount=40000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
        vendor_type="professional",
    )
    first_summary = generate_monthly_tds_summary(session, user.id, "2025-06")
    assert first_summary == {"total_tds_deducted": 4000.0}
    assert session.query(TDSLiability).count() == 1

    create_invoice_with_tds(
        session=session,
        user_id=user.id,
        invoice_number="TUP-2",
        invoice_date=date(2025, 6, 18),
        amount=50000.0,
        gst_rate=18.0,
        transaction_type="purchase",
        is_interstate=False,
        vendor_type="professional",
    )
    second_summary = generate_monthly_tds_summary(session, user.id, "2025-06")
    assert second_summary == {"total_tds_deducted": 9000.0}
    assert session.query(TDSLiability).count() == 1


def test_create_invoice_with_tds_respects_period_lock():
    session = build_session()
    user = seed_user(session, "tds_lock_user@example.com")

    session.add(
        AccountingPeriod(
            user_id=user.id,
            year_month="2025-06",
            is_closed=True,
        )
    )
    session.commit()

    with pytest.raises(Exception, match="Period is closed. Cannot modify."):
        create_invoice_with_tds(
            session=session,
            user_id=user.id,
            invoice_number="LOCKED-TDS-1",
            invoice_date=date(2025, 6, 10),
            amount=40000.0,
            gst_rate=18.0,
            transaction_type="purchase",
            is_interstate=False,
            vendor_type="professional",
        )

    assert session.query(Invoice).count() == 0
