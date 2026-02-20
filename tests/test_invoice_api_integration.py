from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
from app.database import Base
from app.gst_service import create_invoice_with_tds
from app.models import User


def build_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def test_invoice_creation_and_summary_endpoints(monkeypatch):
    SessionLocal = build_session_factory()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main_module.Base.metadata, "create_all", lambda *args, **kwargs: None)
    main_module.app.dependency_overrides[main_module.get_db] = override_get_db

    with SessionLocal() as db:
        user = User(email="invoice_api_user@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    with TestClient(main_module.app) as client:
        create_response = client.post(
            "/invoice",
            json={
                "user_id": user_id,
                "invoice_number": "API-INV-1",
                "invoice_date": "2025-06-05",
                "amount": 100000.0,
                "gst_rate": 18.0,
                "transaction_type": "sale",
                "is_interstate": False,
            },
        )
        assert create_response.status_code == 200
        payload = create_response.json()
        assert payload["invoice_number"] == "API-INV-1"
        assert payload["cgst"] == 9000.0
        assert payload["sgst"] == 9000.0
        assert payload["igst"] == 0.0

        gst_summary = client.get(f"/gst-summary/{user_id}/2025-06")
        assert gst_summary.status_code == 200
        assert gst_summary.json() == {
            "output_gst": 18000.0,
            "input_gst": 0.0,
            "net_payable": 18000.0,
        }

    main_module.app.dependency_overrides.clear()


def test_tds_summary_endpoint_reads_monthly_totals(monkeypatch):
    SessionLocal = build_session_factory()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main_module.Base.metadata, "create_all", lambda *args, **kwargs: None)
    main_module.app.dependency_overrides[main_module.get_db] = override_get_db

    with SessionLocal() as db:
        user = User(email="tds_api_user@example.com")
        db.add(user)
        db.commit()
        db.refresh(user)

        create_invoice_with_tds(
            session=db,
            user_id=user.id,
            invoice_number="API-TDS-1",
            invoice_date="2025-06-01",
            amount=40000.0,
            gst_rate=18.0,
            transaction_type="purchase",
            is_interstate=False,
            vendor_type="professional",
        )
        user_id = user.id

    with TestClient(main_module.app) as client:
        summary = client.get(f"/tds-summary/{user_id}/2025-06")
        assert summary.status_code == 200
        assert summary.json() == {"total_tds_deducted": 4000.0}

    main_module.app.dependency_overrides.clear()
