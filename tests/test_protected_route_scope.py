from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.main as main_module
import app.auth as auth_module
from app.database import Base
from app.models import User


def build_session_factory():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register(client: TestClient, email: str, role: str) -> int:
    response = client.post(
        "/register",
        json={"email": email, "password": "StrongPass#123", "role": role},
    )
    assert response.status_code == 200
    return int(response.json()["id"])


def login(client: TestClient, email: str) -> str:
    response = client.post("/login", json={"email": email, "password": "StrongPass#123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_ca_cannot_manage_other_users_but_admin_can(monkeypatch):
    SessionLocal = build_session_factory()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main_module.Base.metadata, "create_all", lambda *args, **kwargs: None)
    main_module.app.dependency_overrides[main_module.get_db] = override_get_db
    main_module.app.dependency_overrides[auth_module.get_db] = override_get_db

    with TestClient(main_module.app) as client:
        target_user_id = register(client, "scope_target@example.com", "business")
        ca_user_id = register(client, "scope_ca@example.com", "ca")
        admin_user_id = register(client, "scope_admin@example.com", "admin")

        assert ca_user_id != target_user_id
        assert admin_user_id != target_user_id

        ca_token = login(client, "scope_ca@example.com")
        admin_token = login(client, "scope_admin@example.com")

        ca_close = client.post(
            f"/close-period/{target_user_id}/2025-06",
            headers=auth_header(ca_token),
        )
        assert ca_close.status_code == 403

        admin_close = client.post(
            f"/close-period/{target_user_id}/2025-06",
            headers=auth_header(admin_token),
        )
        assert admin_close.status_code == 200

        ca_audit = client.get(f"/audit/{target_user_id}", headers=auth_header(ca_token))
        assert ca_audit.status_code == 403

        admin_audit = client.get(f"/audit/{target_user_id}", headers=auth_header(admin_token))
        assert admin_audit.status_code == 200

    main_module.app.dependency_overrides.clear()
